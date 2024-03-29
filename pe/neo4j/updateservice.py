"""
Created on 23.3.2020

@author: jm
"""
import logging
import traceback
from neo4j.exceptions import ClientError

logger = logging.getLogger("stkserver")
from datetime import date  # , datetime

from bl.base import Status
from bl.person_name import Name
from bl.place import PlaceBl, PlaceName

from pe.dataservice import ConcreteService
from .cypher.cy_batch_audit import CypherBatch, CypherAudit
from .cypher.cy_person import CypherPerson
from .cypher.cy_refname import CypherRefname
from .cypher.cy_family import CypherFamily
from .cypher.cy_place import CypherPlace, CypherPlaceMerge
from .cypher.cy_gramps import CypherObjectWHandle


class Neo4jUpdateService(ConcreteService):
    """
    This service for Neo4j database maintains transaction and executes
    different read/write/update functions.

    Referenced as shareds.dataservices["update"] class.
    """

    def __init__(self, driver):
        """Create a writer/updater object with db driver and user context.

        :param: driver             neo4j.DirectDriver object
        """
        print(f"#~~~~{self.__class__.__name__} init")
        self.driver = driver
        # self.tx = driver.session().begin_transaction()

    def ds_commit(self):
        """Commit transaction."""
        #         if self.tx.closed():
        #             print("Transaction already closed!")
        #             return {'status':Status.OK}
        try:
            self.tx.commit()

            print("Transaction committed")
            return {"status": Status.OK}
        except Exception as e:
            msg = f"{e.__class__.__name__}, {e}"
            logger.info('-> pe.neo4j.updateservice.Neo4jUpdateService.ds_commit/fail"')
            print("Neo4jUpdateService.ds_commit: Transaction failed " + msg)
            return {"status": Status.ERROR, "statustext": f"Commit failed: {msg}"}

    def ds_rollback(self):
        """Rollback transaction."""
        try:
            self.tx.rollback()
            print("Transaction discarded")
            logger.info("-> pe.neo4j.write_driver.Neo4jUpdateService.ds_rollback")
            return {"status": Status.OK}
        except Exception as e:
            msg = f"{e.__class__.__name__}, {e}"
            logger.info(
                '-> pe.neo4j.updateservice.Neo4jUpdateService.ds_rollback/fail"'
            )
            print("Neo4jUpdateService.ds_rollback: Transaction failed " + msg)
            #             self.blog.log_event({'title':_("Database save failed due to {}".\
            #                                  format(msg)), 'level':"ERROR"})
            return {"status": Status.ERROR, "statustext": f"Rollback failed: {msg}"}

    # ----- Batch Audit -----

    def ds_aqcuire_lock(self, lock_id):
        """Create a lock"""
        self.tx.run(CypherBatch.aquire_lock, lock_id=lock_id)
        return True  # value > 0

    def ds_new_batch_id(self):
        """Find next unused Batch id.

        Returns {id, status, [statustext]}
        """

        # 1. Find the latest Batch id of today from the db
        base = str(date.today())
        ext = 0
        try:
            record = self.tx.run(CypherBatch.batch_find_id, batch_base=base).single()
            if record:
                batch_id = record.get("bid")
                print(f"# Pervious batch_id={batch_id}")
                i = batch_id.rfind(".")
                ext = int(batch_id[i + 1 :])
        except AttributeError as e:
            # Normal exception: this is the first batch of day
            ext = 0
        except Exception as e:
            statustext = f"Neo4jUpdateService.ds_new_batch_id: {e.__class__.name} {e}"
            print(statustext)
            return {"status": Status.ERROR, "statustext": statustext}

        # 2. Form a new batch id
        batch_id = "{}.{:03d}".format(base, ext + 1)

        print("# New batch_id='{}'".format(batch_id))
        return {"status": Status.OK, "id": batch_id}

    def ds_batch_save(self, attr):
        """Creates a Batch node.

        attr = {"mediapath", "file", "id", "user", "status"}

        Batch.timestamp is created in the Cypher clause.
        """
        try:
            result = self.tx.run(CypherBatch.batch_create, b_attr=attr)
            uniq_id = result.single()[0]
            return {"status": Status.OK, "identity": uniq_id}

        except Exception as e:
            statustext = (
                f"Neo4jUpdateService.ds_batch_save failed: {e.__class__.name} {e}"
            )
            return {"status": Status.ERROR, "statustext": statustext}

    def ds_batch_set_status(self, batch, status):
        """Updates Batch node selected by Batch id.

        Batch.timestamp is updated in the Cypher clause.
        """
        try:
            result = self.tx.run(
                CypherBatch.batch_complete, bid=batch.id, user=batch.user, status=status
            )
            uniq_id = result.single()[0]
            return {"status": Status.OK, "identity": uniq_id}

        except Exception as e:
            statustext = f"Neo4jUpdateService.ds_batch_set_status failed: {e.__class__.__name__} {e}"
            return {"status": Status.ERROR, "statustext": statustext}

    # ----- Common objects -----

    def ds_merge_check(self, id1, id2):
        """Check that given objects are mergeable.

        Rules:
        - Objects have same label
        - Both objects have the same type of end relation (OWNS or PASSED)
        """

        class RefObj:
            def __str__(self):
                return f"{self.uniq_id}:{self.label} {self.str}"

        objs = {}
        try:
            result = self.tx.run(CypherAudit.merge_check, id_list=[id1, id2])
            # for root_id, root_str, rel, obj_id, obj_label, obj_str in result:
            for record in result:
                ro = RefObj()
                ro.uniq_id = record["obj_id"]
                ro.label = record["obj_label"]
                ro.str = record["obj_str"]
                ro.root = (
                    record.get("rel"),
                    record.get("root_id"),
                    record.get("root_str"),
                )
                # rint(f'#ds_merge_check {root_id}:{root_str} -[{rel}]-> {obj_id}:{obj_label} {obj_str}')
                print(f"#ds_merge_check {ro.uniq_id}:{ro.label} {ro.str} in {ro.root}")
                if ro.uniq_id in objs.keys():
                    # Error if current uniq_id exists twice
                    msg = f"Object {ro} has two roots {objs[ro.uniq_id].root} and {ro.root}"
                    return {"status": Status.ERROR, "statustext": msg}
                for i, obj2 in objs.items():
                    print(f"#ds_merge_check {obj2} <> {ro}")
                    if i == ro.uniq_id:
                        continue
                    # Error if different labels or has different root node
                    if obj2.label != ro.label:
                        msg = f"Objects {obj2} and {ro} are different"
                        return {"status": Status.ERROR, "statustext": msg}
                    if obj2.root[1] != ro.root[1]:
                        msg = (
                            f"Object {ro} has different roots {obj2.root} and {ro.root}"
                        )
                        return {"status": Status.ERROR, "statustext": msg}
                objs[ro.uniq_id] = ro

            if len(objs) == 2:
                print(f"ds_merge_check ok {objs}")
                return {"status": Status.OK}
            else:
                msg = f"ds_merge_check failed, found {len(objs)} objects"
                return {"status": Status.ERROR, "statustext": msg}

        except ClientError as e:
            # traceback.print_exc()
            return {
                "status": Status.ERROR,
                "statustext": "Neo4jUpdateService.ds_merge_check "
                f"{id1}<-{id2} failed: {e.__class__.__name__} {e}",
            }

    def ds_obj_save_and_link(self, obj, **kwargs):
        """Saves given object to database

        :param: batch_id    Current Batch (batch) --> (obj)
        _param: parent_id   Parent object to link (parent) --> (obj)
        """
        obj.save(self.tx, **kwargs)

    def ds_obj_remove_gramps_handles(self, batch_id):
        """Remove all Gramps handles."""
        status = Status.OK
        total = 0
        unlinked = 0
        # Remove handles from nodes connected to given Batch
        result = self.tx.run(CypherBatch.remove_all_handles, batch_id=batch_id)
        for count, label in result:
            print(f"# - cleaned {count} {label} handles")
            total += count
        # changes = result.summary().counters.properties_set

        # Find handles left: missing link (:Batch) --> (x)
        result = self.tx.run(CypherBatch.find_unlinked_nodes)
        for count, label in result:
            print(
                f"Neo4jUpdateService.ds_obj_remove_gramps_handles WARNING: Found {count} {label} not linked to batch"
            )
            unlinked += count
        return {"status": status, "count": total, "unlinked": unlinked}

    # ----- Note -----

    # ----- Media -----

    def ds_create_link_medias_w_handles(self, uniq_id: int, media_refs: list):
        """Save media object and it's Note and Citation references
        using their Gramps handles.

        media_refs:
            media_handle      # Media object handle
            media_order       # Media reference order nr
            crop              # Four coordinates
            note_handles      # list of Note object handles
            citation_handles  # list of Citation object handles
        """
        doing = "?"
        try:
            for resu in media_refs:
                r_attr = {"order": resu.media_order}
                if resu.crop:
                    r_attr["left"] = resu.crop[0]
                    r_attr["upper"] = resu.crop[1]
                    r_attr["right"] = resu.crop[2]
                    r_attr["lower"] = resu.crop[3]
                doing = f"(src:{uniq_id}) -[{r_attr}]-> Media {resu.media_handle}"
                #                 print(doing)
                result = self.tx.run(
                    CypherObjectWHandle.link_media,
                    root_id=uniq_id,
                    handle=resu.media_handle,
                    r_attr=r_attr,
                )
                media_uid = result.single()[0]  # for media object

                for handle in resu.note_handles:
                    doing = f"{media_uid}->Note {handle}"
                    self.tx.run(
                        CypherObjectWHandle.link_note, root_id=media_uid, handle=handle
                    )

                for handle in resu.citation_handles:
                    doing = f"{media_uid}->Citation {handle}"
                    self.tx.run(
                        CypherObjectWHandle.link_citation,
                        root_id=media_uid,
                        handle=handle,
                    )

        except Exception as err:
            logger.error(
                f"Neo4jUpdateService.create_link_medias_by_handles {doing}: {err}"
            )

    # ----- Place -----

    def ds_place_set_default_names(self, place_id, fi_id, sv_id):
        """Creates default links from Place to fi and sv PlaceNames.

        - place_id      Place object id
        - fi_id         PlaceName object id for fi
        - sv_id         PlaceName object id for sv
        """
        try:
            if fi_id == sv_id:
                result = self.tx.run(
                    CypherPlace.link_name_lang_single, place_id=place_id, fi_id=fi_id
                )
            else:
                result = self.tx.run(
                    CypherPlace.link_name_lang,
                    place_id=place_id,
                    fi_id=fi_id,
                    sv_id=sv_id,
                )
            x = None
            for x, _fi, _sv in result:
                # print(f"# Linked ({x}:Place)-['fi']->({fi}), -['sv']->({sv})")
                pass

            if not x:
                logger.warning(
                    "eo4jWriteDriver.place_set_default_names: not created "
                    f"Place {place_id}, names fi:{fi_id}, sv:{sv_id}"
                )

        except Exception as err:
            logger.error(f"Neo4jUpdateService.place_set_default_names: {err}")
            return err

    def ds_places_merge(self, id1, id2):
        """Merges given two Place objects using apoc library."""
        try:
            self.tx.run(CypherPlaceMerge.delete_namelinks, id=id1)
            record = self.tx.run(
                CypherPlaceMerge.merge_places, id1=id1, id2=id2
            ).single()
            node = record["node"]
            place = PlaceBl.from_node(node)
            name_nodes = record["names"]
            place.names = [PlaceName.from_node(n) for n in name_nodes]
        except ClientError as e:
            # traceback.print_exc()
            return {
                "status": Status.ERROR,
                "statustext": f"Neo4jUpdateService.ds_places_merge {id1}<-{id2} failed: {e.__class__.__name__} {e}",
            }

        return {"status": Status.OK, "place": place}

    # ----- Repository -----

    # ----- Source -----

    # ----- Citation -----

    # ----- Event -----

    # ----- Person -----

    def ds_get_personnames(self, uniq_id=None):
        """Picks all Name versions of this Person or all persons.

        Use optionally refnames or sortname for person selection
        """
        if uniq_id:
            result = self.tx.run(CypherPerson.get_names, pid=uniq_id)
        else:
            result = self.tx.run(CypherPerson.get_all_persons_names)
        # <Record
        #    pid=82
        #    name=<Node id=83 labels=frozenset({'Name'})
        #        properties={'title': 'Sir', 'firstname': 'Jan Erik', 'surname': 'Mannerheimo',
        #            'prefix': '', 'suffix': 'Jansson', 'type': 'Birth Name', 'order': 0}> >

        return [(record["pid"], record["name"]) for record in result]

    def _set_people_lifetime_estimates(self, uids=[]):
        """Get estimated lifetimes to Person.dates for given person.uniq_ids.

        :param: uids  list of uniq_ids of Person nodes; empty = all lifetimes
        """
        from models import lifetime
        from bl.dates import DR

        personlist = []
        personmap = {}
        res = {"status": Status.OK}
        try:
            if uids:
                result = self.tx.run(
                    CypherPerson.fetch_selected_for_lifetime_estimates, idlist=uids
                )
            else:
                result = self.tx.run(CypherPerson.fetch_all_for_lifetime_estimates)
            # RETURN p, id(p) as pid,
            #     COLLECT(DISTINCT [e,r.role]) AS events,
            #     COLLECT(DISTINCT [fam_event,r2.role]) AS fam_events,
            #     COLLECT(DISTINCT [c,id(c)]) as children,
            #     COLLECT(DISTINCT [parent,id(parent)]) as parents
            for record in result:
                # Person
                p = lifetime.Person()
                p.pid = record["pid"]
                p.gramps_id = record["p"]["id"]

                # Person and family event dates
                events = record["events"]
                fam_events = record["fam_events"]
                for e, role in events + fam_events:
                    if e is None:
                        continue
                    # print("e:",e)
                    eventtype = e["type"]
                    datetype = e["datetype"]
                    datetype1 = None
                    datetype2 = None
                    if datetype == DR["DATE"]:
                        datetype1 = "exact"
                    elif datetype == DR["BEFORE"]:
                        datetype1 = "before"
                    elif datetype == DR["AFTER"]:
                        datetype1 = "after"
                    elif datetype in [DR["BETWEEN"], DR["PERIOD"]]:
                        datetype1 = "after"
                        datetype2 = "before"
                    date1 = e["date1"]
                    date2 = e["date2"]
                    if datetype1 and date1 is not None:
                        year1 = date1 // 1024
                        ev = lifetime.Event(eventtype, datetype1, year1, role)
                        p.events.append(ev)
                    if datetype2 and date2 is not None:
                        year2 = date2 // 1024
                        ev = lifetime.Event(eventtype, datetype2, year2, role)
                        p.events.append(ev)

                # List Parent and Child identities
                p.parent_pids = []
                for _parent, pid in record["parents"]:
                    if pid:
                        p.parent_pids.append(pid)
                p.child_pids = []
                for _parent, pid in record["children"]:
                    if pid:
                        p.child_pids.append(pid)

                personlist.append(p)
                personmap[p.pid] = p

            # Add parents and children to lifetime.Person objects
            for p in personlist:
                for pid in p.parent_pids:
                    p.parents.append(personmap[pid])
                for pid in p.child_pids:
                    p.children.append(personmap[pid])
            lifetime.calculate_estimates(personlist)

            for p in personlist:
                result = self.tx.run(
                    CypherPerson.update_lifetime_estimate,
                    id=p.pid,
                    birth_low=p.birth_low.getvalue(),
                    death_low=p.death_low.getvalue(),
                    birth_high=p.birth_high.getvalue(),
                    death_high=p.death_high.getvalue(),
                )

            res["count"] = len(personlist)
            # print(f"Estimated lifetime for {res['count']} persons")
            return res

        except Exception as e:
            msg = f"Neo4jUpdateService._set_people_lifetime_estimates: {e.__class__.__name__} {e}"
            print(f"Error {msg}")
            traceback.print_exc()
            return {"status": Status.ERROR, "statustext": msg}

    def ds_build_refnames(self, person_uid: int, name: Name):
        """Set Refnames to the Person with given uniq_id."""

        def link_to_refname(person_uid, nm, use):
            result = self.tx.run(
                CypherRefname.link_person_to, pid=person_uid, name=nm, use=use
            )
            rid = result.single()[0]
            if rid is None:
                raise RuntimeError(f"Error for ({person_uid})-->({nm})")
            return rid

        count = 0
        try:
            # 1. firstnames
            if name.firstname and name.firstname != "N":
                for nm in name.firstname.split(" "):
                    if link_to_refname(person_uid, nm, "firstname"):
                        count += 1

            # 2. surname and patronyme
            if name.surname and name.surname != "N":
                if link_to_refname(person_uid, name.surname, "surname"):
                    count += 1

            if name.suffix:
                if link_to_refname(person_uid, name.suffix, "patronyme"):
                    count += 1

        except Exception as e:
            msg = f"Neo4jUpdateService.ds_build_refnames: {e.__class__.__name__} {e}"
            print(msg)
            return {"status": Status.ERROR, "count": count, "statustext": msg}

        return {"status": Status.OK, "count": count}

    def _update_person_confidences(self, uniq_id: int):
        """Collect Person confidence from Person and Event nodes and store result in Person.

        Voidaan lukea henkilön tapahtumien luotettavuustiedot kannasta
        """
        sumc = 0
        try:
            result = self.tx.run(CypherPerson.get_confidences, id=uniq_id)
            for record in result:
                # Returns person.uniq_id, COLLECT(confidence) AS list
                orig_conf = record["confidence"]
                confs = record["list"]
                for conf in confs:
                    sumc += int(conf)

            if confs:
                conf_float = sumc / len(confs)
                new_conf = "%0.1f" % conf_float  # string with one decimal
            else:
                new_conf = ""
            if orig_conf != new_conf:
                # Update confidence needed
                self.tx.run(
                    CypherPerson.set_confidence, id=uniq_id, confidence=new_conf
                )

                return {"confidence": new_conf, "status": Status.UPDATED}
            return {"confidence": new_conf, "status": Status.OK}

        except Exception as e:
            msg = f"Neo4jUpdateService._update_person_confidences: {e.__class__.__name__} {e}"
            print(msg)
            return {"confidence": new_conf, "status": Status.ERROR, "statustext": msg}

    def _link_person_to_refname(self, pid, name, reftype):
        """Connects a reference name of type reftype to Person(pid)."""
        from bl.refname import REFTYPES

        if not name > "":
            logging.warning("Missing name {} for {} - not added".format(reftype, name))
            return
        if reftype not in REFTYPES:
            raise ValueError("Invalid reftype {}".format(reftype))
        try:
            _result = self.tx.run(
                CypherRefname.link_person_to, pid=pid, name=name, use=reftype
            )
            return {"status": Status.OK}

        except Exception as e:
            msg = f"Neo4jUpdateService._link_person_to_refname: person={pid}, {e.__class__.__name__}, {e}"
            print(msg)
            return {"status": Status.ERROR, "statustext": msg}

    # ----- Refname -----

    def _get_person_by_uid(self, uniq_id: int):
        """ Set Person object by uniq_id."""
        try:
            self.tx.run(CypherPerson.get_person_by_uid, uid=uniq_id)
            return {"status": Status.OK}
        except Exception as e:
            msg = f"Neo4jUpdateService._get_person_by_uid: person={uniq_id}, {e.__class__.__name__}, {e}"
            print(msg)
            return {"status": Status.ERROR, "statustext": msg}

    def _set_person_sortname(self, uniq_id: int, sortname):
        """ Set sortname property to Person object by uniq_id."""
        try:
            self.tx.run(CypherPerson.set_sortname, uid=uniq_id, key=sortname)
            return {"status": Status.OK}
        except Exception as e:
            msg = f"Neo4jUpdateService._set_person_sortname: person={uniq_id}, {e.__class__.__name__}, {e}"
            print(msg)
            return {"status": Status.ERROR, "statustext": msg}

    # ----- Family -----

    def _set_family_dates_sortnames(
        self, uniq_id, dates, father_sortname, mother_sortname
    ):
        """Update Family dates and parents' sortnames.

        :param:    uniq_id      family identity
        :dates:    dict         representing DateRange for family
                                (marriage ... death or divorce

        Called from self._set_family_calculated_attributes only
        """
        f_attr = {
            "father_sortname": father_sortname,
            "mother_sortname": mother_sortname,
        }
        if dates:
            f_attr.update(dates)

        result = self.tx.run(CypherFamily.set_dates_sortname, id=uniq_id, f_attr=f_attr)
        counters = result.consume().counters
        cnt = counters.properties_set
        return {"status": Status.OK, "count": cnt}

    def _set_family_calculated_attributes(self, uniq_id=None):
        """Set Family sortnames and estimated marriage DateRange.

        :param: uids  list of uniq_ids of Person nodes; empty = all lifetimes

        Called from bp.gramps.xml_dom_handler.DOM_handler.set_family_calculated_attributes

        Set Family.father_sortname and Family.mother_sortname using the data in Person
        Set Family.date1 using the data in marriage Event
        Set Family.datetype and Family.date2 using the data in divorce or death Events
        """
        from bl.dates import DateRange, DR

        dates_count = 0
        sortname_count = 0
        status = Status.OK

        try:
            # Process each family
            #### Todo Move and refactor to bl.FamilyBl
            # result = Family_combo.get_dates_parents(my_tx, uniq_id)
            result = self.tx.run(CypherFamily.get_dates_parents, id=uniq_id)
            for record in result:
                # RETURN father.sortname AS father_sortname, father_death.date1 AS father_death_date,
                #        mother.sortname AS mother_sortname, mother_death.date1 AS mother_death_date,
                #        event.date1 AS marriage_date, divorce_event.date1 AS divorce_date
                father_death_date = record["father_death_date"]
                mother_death_date = record["mother_death_date"]
                marriage_date = record["marriage_date"]
                divorce_date = record["divorce_date"]

                # Dates calculation
                dates = None
                end_date = None
                if (
                    not divorce_date
                    and father_death_date
                    and father_death_date < mother_death_date
                    or not divorce_date
                    and not mother_death_date
                    and father_death_date
                ):
                    end_date = father_death_date
                elif not divorce_date and mother_death_date:
                    end_date = mother_death_date
                elif divorce_date:
                    end_date = divorce_date
                if marriage_date:
                    if end_date:
                        dates = DateRange(DR["PERIOD"], marriage_date, end_date)
                    else:
                        dates = DateRange(DR["DATE"], marriage_date)
                elif end_date:
                    dates = DateRange(DR["BEFORE"], end_date)
                dates_dict = dates.for_db() if dates else None

                # Save the dates from Event node and sortnames from Person nodes
                ret = self._set_family_dates_sortnames(
                    uniq_id,
                    dates_dict,
                    record.get("father_sortname"),
                    record.get("mother_sortname"),
                )
                if Status.has_failed(ret):
                    return ret
                # print('Neo4jUpdateService._set_family_calculated_attributes: '
                #      f'id={uniq_id} properties_set={ret.get("count","none")}')
                dates_count += 1
                sortname_count += 1

            return {
                "status": status,
                "dates": dates_count,
                "sortnames": sortname_count,
                "statustext": ret.get("statustext", ""),
            }

        except Exception as e:
            msg = f"Neo4jUpdateService._set_family_calculated_attributes: person={uniq_id}, {e.__class__.__name__}, {e}"
            print(msg)
            return {"status": Status.ERROR, "statustext": msg}
