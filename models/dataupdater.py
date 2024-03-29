#   Isotammi Genealogical Service for combining multiple researchers' results.
#   Created in co-operation with the Genealogical Society of Finland.
#
#   Copyright (C) 2016-2021  Juha Mäkeläinen, Jorma Haapasalo, Kari Kujansuu,
#                            Timo Nallikari, Pekka Valta
#   See the LICENSE file.

# Taapeli harjoitustyö @ Sss 2016
# JMä 11.4.2016

# import time
from flask_babelex import _

# from sys import stderr

# from bp.gramps.batchlogger import BatchLog
from models.gen.user import User
from bl.person import PersonBl

# from bl.person_name import Name
# from bl.family import FamilyBl

# from models.gen.person import Person
# from models.gen.place import Place
# from models.gen.person_name import Name
# from models.gen.refname import Refname
# from models.gen.person_combo import Person_combo
from models.gen.family_combo import Family_combo
from bl.dates import DateRange, DR


def make_place_hierarchy_properties(tx=None, place=None):
    """Connects places to the upper level places.

    TODO: NOT IN USE
    """
    hierarchy_count = 0

    if tx:
        my_tx = tx
    else:
        my_tx = User.beginTransaction()

    place.make_hierarchy(my_tx, place)

    hierarchy_count += 1

    return hierarchy_count

    if not tx:
        # Close my own created transaction
        User.endTransaction(my_tx)


# def set_confidence_values(tx, uniq_id=None, batch_logger=None): --> bl.person.PersonBl.set_confidence
#     """ Sets a quality rate for one or all Persons.
#
#         Asettaa henkilölle laatuarvion.
#
#         Person.confidence is mean of all Citations used for Person's Events
#     """
#     counter = 0
#     t0 = time.time()
#     print('models.dataupdater.set_confidence_values: NOT IMPLEMENTED', file=stderr)
#     return
#     #=======================================================
#     result = PersonBl.get_confidence(uniq_id)
#     for record in result:
#         p = PersonBl()
#         p.uniq_id = record["uniq_id"]
#
#         if len(record["list"]) > 0:
#             sumc = 0
#             for ind in record["list"]:
#                 sumc += int(ind)
#
#             confidence = sumc/len(record["list"])
#             p.confidence = "%0.1f" % confidence # string with one decimal
#         p.set_confidence(tx)
#
#         counter += 1
#
#     if isinstance(batch_logger, Batch):
#         batch_logger.log_event({'title':"Confidences set",
#                                 'count':counter, 'elapsed':time.time()-t0})
#     return


def set_person_estimated_dates(uids=[]):
    """Sets an estimated lifetime in Person.dates.

    Asettaa kaikille tai valituille henkilölle arvioidut syntymä- ja kuolinajat

    The properties in Person node are datetype, date1, and date2.
    With transaction, see gramps_loader.DOM_handler.set_estimated_dates_tr

    Called from bp.admin.routes.estimate_dates
    """
    my_tx = User.beginTransaction()

    cnt = PersonBl.estimate_lifetimes(my_tx, uids)

    msg = _("Estimated {} person lifetimes").format(cnt)
    User.endTransaction(my_tx)

    return msg


def set_family_calculated_attributes(tx=None, uniq_id=None):
    """Set Family sortnames and estimated DateRange.

    Called from bp.gramps.xml_dom_handler.DOM_handler.set_family_calculated_attributes

    Set Family.father_sortname and Family.mother_sortname using the data in Person
    Set Family.date1 using the data in marriage Event
    Set Family.datetype and Family.date2 using the data in divorce or death Events
    If handler is defined
    - if there is transaction tx, use it, else create a new
    """
    dates_count = 0
    sortname_count = 0

    my_tx = tx or User.beginTransaction()
    # Process each family
    #### Todo Move and refactor to bl.FamilyBl
    result = Family_combo.get_dates_parents(my_tx, uniq_id)
    for record in result:
        father_sortname = record["father_sortname"]
        father_death_date = record["father_death_date"]
        mother_sortname = record["mother_sortname"]
        mother_death_date = record["mother_death_date"]
        marriage_date = record["marriage_date"]
        divorce_date = record["divorce_date"]

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

        # Copy the dates from Event node and sortnames from Person nodes
        set_family_calculated_attributes(
            my_tx, uniq_id, dates, father_sortname, mother_sortname
        )
        dates_count += 1
        sortname_count += 1

    if not tx:
        # Close my own created transaction
        User.endTransaction(my_tx)

    return (dates_count, sortname_count)


# def set_person_name_properties(tx=None, uniq_id=None, ops=['refname', 'sortname']): #-> bl.person.PersonBl.set_person_name_properties
#     """ Set Refnames to all Persons or one Person with given uniq_id;
#         also sets Person.sortname using the default name
#
#         Called from bp.gramps.xml_dom_handler.DOM_handler.set_family_calculated_attributes,
#                     bp.admin.routes.set_all_person_refnames
#
#         If handler is defined
#         - if there is transaction tx, use it, else create a new
#     """
#     sortname_count = 0
#     refname_count = 0
#     do_refnames = 'refname' in ops
#     do_sortname = 'sortname' in ops
#
#     if tx:
#         my_tx = tx
#     else:
#         my_tx = User.beginTransaction()
#
#     # Process each name
#     names = Name.get_personnames(my_tx, uniq_id)
#     for name in names:
#
#         if do_refnames:
#             # Build new refnames
#
#             # 1. firstnames
#             if name.firstname and name.firstname != 'N':
#                 for nm in name.firstname.split(' '):
#                     Refname.link_to_refname(my_tx, name.person_uid, nm, 'firstname')
#                     refname_count += 1
#
#             # 2. surname and patronyme
#             if name.surname and name.surname != 'N':
#                 Refname.link_to_refname(my_tx, name.person_uid, name.surname, 'surname')
#                 refname_count += 1
#
#             if name.suffix:
#                 Refname.link_to_refname(my_tx, name.person_uid, name.suffix, 'patronyme')
#                 refname_count += 1
#
#         if do_sortname and name.order == 0:
#
#             # If default name, store sortname key to Person node
#             PersonBl.set_sortname(my_tx, name.person_uid, name)
#             sortname_count += 1
#
#     if not tx:
#         # Close my self created transaction
#         User.endTransaction(my_tx)
#
#     return (refname_count, sortname_count)


# Moved to bp.obsolete_tools.models.dataupdater.joinpersons
# def joinpersons(base_id, join_ids):
#     """ Yhdistetään henkilöön oid=base_id toiset henkilöt, joiden oid:t on
#         listassa join_ids.
#
#         Yhdistämisen tulisi koskea attribuutteja ja tapahtumia,
#         jotka liittyvät ko. henkilöiin
#     """
#     logging.debug('Pitäisi yhdistää ' + str(base_id) + " + " + str(join_ids) )
#     pass
