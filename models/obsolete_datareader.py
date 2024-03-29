# coding=UTF-8
#
# Methods to process stk data using methods from models.gen
#
# Taapeli harjoitustyö @ Sss 2016
# JMä 12.1.2016

import logging
import time
from sys import stderr

from flask_babelex import _

# from flask import flash
from flask import request  # , flash, render_template, redirect, url_for
from flask import session as user_session
from flask_security import current_user  # , login_required #, roles_accepted

from operator import itemgetter

from bl.person_name import Name

# from models.dbutil import Datefrom
from models.gen.event import Event
from models.gen.event_combo import Event_combo
from models.gen.family_combo import Family_combo  # ,  Family
from models.gen.note import Note
from models.gen.obsolete_media import Media

# from models.gen.person import SEX_MALE #, SEX_FEMALE
from models.gen.person_combo import Person_combo, Person_as_member

# from models.gen.person_name import Name
# from models.gen.place import Place
from models.gen.place_combo import Place_combo
from bl.refname import Refname
from models.gen.citation import Citation  # , NodeRef
from models.gen.source import Source
from models.gen.repository import Repository
from bl.dates import DateRange
from ui.user_context import UserContext

# import traceback


def obsolete_read_persons_with_events(
    keys=None, args={}
):  # , user=None, take_refnames=False, order=0):
    """Reads Person Name and Event objects for display.

    OBSOLETE. Called from bp.scene.routes.obsolete_show_persons_by_refname

    Filter persons by args['context_code'].

    Returns Person objects, whith included Events and Names
    and optionally Refnames (if args['take_refnames'])

    NOTE. Called with
        keys = ('uniq_id', uid)     in bp.scene.routes.show_person_list
        keys = ('refname', refname) in bp.scene.routes.show_persons_by_refname
        keys = ('all',)             in bp.scene.routes.show_all_persons_list

        keys = None                 in routes.show_table_data
        keys = ['surname',value]    in routes.pick_selection
        keys = ("uniq_id",value)    in routes.pick_selection
    """

    persons = Person_combo.get_person_w_events(
        keys, args=args
    )  # user, take_refnames=take_refnames, order=order)
    return persons


def obsolete_read_refnames():
    """Reads all Refname objects for table display
    (n:Refname)-[r]->(m)
    """
    t0 = time.time()
    recs = Refname.get_refnames()

    logging.info("TIME get_refnames {} sek".format(time.time() - t0))

    return recs


def obsolete_recreate_refnames():
    summary = Refname.recreate_refnames()
    return str(summary)


# def read_typed_refnames(reftype):
#     """ Reads selected Refname objects for display
#     """
#     namelist = []
#     t0 = time.time()
#     if not (reftype and reftype != ""):
#         raise AttributeError("Please, select desired reftype?")
#
#     recs = Refname.get_typed_refnames(reftype)
# # Esimerkki:
# # >>> for x in v_names: print(x)
# # <Record a.oid=3 a.name='Aabi' a.sex=None a.source='harvinainen'
# #         base=[[2, 'Aapeli', None]] other=[[None, None, None]]>
# # <Record a.oid=5 a.name='Aabraham' a.sex='1' a.source='Pojat 1990-luvulla'
# #         base=[[None, None, None]] other=[[None, None, None]]>
# # <Record a.oid=6 a.name='Aabrahami' a.sex='0' a.source='harvinainen'
# #         base=[[7, 'Aappo', None]] other=[[None, None, None]]>
# # >>> for x in v_names: print(x[1])
# # Aabrahami
# # Aabrami
# # Aaca
#
# #a.oid  a.name  a.sex  a.source   base                 other
# #                                     [oid, name, sex]  [oid, name, sex]
# #-----  ------  --------  --------   ----                 -----
# #3493   Aake	F	  Messu- ja  [[null, null, null], [[3495, Aakke, null],
# #                         kalenteri   [null, null, null],  [3660, Acatius, null],
# #                                     [null, null, null],  [3662, Achat, null],
# #                                     [null, null, null],  [3664, Achatius, M],
# #                                     [null, null, null],  [3973, Akatius, null],
# #                                     [null, null, null],  [3975, Ake, null],
# #                                     [null, null, null]]  [3990, Akke, null]]
# #3495   Aakke   null     harvinainen [[3493, Aake, F]]    [[null, null, null]]
#
#     for rec in recs:
# #        logging.debug("oid={}, name={}, sex={}, source={}, base={}, other={}".\
# #               format( rec[0], rec[1],  rec[2],    rec[3],    rec[4],  rec[5]))
#         # Luodaan nimi
#         r = Refname(rec['a.name'])
#         r.oid = rec['a.id']
#         if rec['a.sex']:
#             r.sex = rec['a.sex']
#         if rec['a.source']:
#             r.source= rec['a.source']
#
#         # Luodaan mahdollinen kantanimi, johon tämä viittaa (yksi?)
#         baselist = []
#         for fld in rec['base']:
#             if fld[0]:
#                 b = Refname(fld[1])
#                 b.oid = fld[0]
#                 if fld[2]:
#                     b.sex = fld[2]
#                 baselist.append(b)
#
#         # Luodaan lista muista nimistä, joihin tämä viittaa
#         otherlist = []
#         for fld in rec['other']:
#             if fld[0]:
#                 o = Refname(fld[1])
#                 o.oid = fld[0]
#                 if fld[2]:
#                     o.sex = fld[2]
#                 otherlist.append(o)
#
#         namelist.append((r,baselist,otherlist))
#
#     logging.info("TIME get_named_refnames {} sek".format(time.time()-t0))
#
#     return (namelist)


def obsolete_read_cite_sour_repo(uniq_id=None):
    """Lukee tietokannasta Repository-, Source- ja Citation- objektit näytettäväksi.

    Called from bp.obsolete_tools.routes.pick_selection  -  NOT IN USE?
    """

    sources = []
    result_cite = Event_combo.get_event_cite(uniq_id)
    for record_cite in result_cite:
        pid = record_cite["id"]
        e = Event_combo()
        e.uniq_id = pid
        if record_cite["type"]:
            e.type = record_cite["type"]
        #         if record_cite['date']:
        #             e.date = record_cite['date']
        if record_cite["dates"]:
            e.dates = DateRange(record_cite["dates"])

        for source_cite in record_cite["sources"]:
            c = Citation()
            c.uniq_id = source_cite[0]
            c.dateval = source_cite[1]
            c.page = source_cite[2]
            c.confidence = source_cite[3]

            c.get_sourceref_hlink()
            if c.source_handle != "":
                s = Source()
                s.uniq_id = c.source_handle
                result_source = s.get_source_data()
                for record_source in result_source:
                    if record_source["stitle"]:
                        s.stitle = record_source["stitle"]
                    if record_source["sauthor"]:
                        s.sauthor = record_source["sauthor"]
                    if record_source["spubinfo"]:
                        s.spubinfo = record_source["spubinfo"]

                    s.get_repositories_w_notes()

                c.source = s  # s.append(s)
            e.citations.append(c)

        sources.append(e)

    return sources


# def obsolete_read_medias(uniq_id=None):
#     """ Lukee tietokannasta Media-objektit näytettäväksi.
#     """
#
#     media = []
#     result = Media.get_medias(uniq_id)
#     for record in result:
#         node = record[0]
#         o = Media.from_node(node)
#         media.append(o)
#
#     return (media)


def obsolete_get_repositories(uniq_id=None):
    """Lukee tietokannasta Repository- ja Source- objektit näytettäväksi

        (Korvaa read_repositories()
    ╒════════╤════════╤════════╤════════╤════════╤═══════╤════════╤════════╕
    │"uniq_id│"rname" │"type"  │"change"│"handle"│"id"   │"sources│"notes" │
    │"       │        │        │        │        │       │"       │        │
    ╞════════╪════════╪════════╪════════╪════════╪═══════╪════════╪════════╡
    │25979   │"Haminan│"Library│"1526233│"_de18a0│"R0000"│[[25992,│[[...], │
    │        │ kaupung│"       │479"    │b2d546e2│       │"Haminan│]       │
    │        │inarkist│        │        │22251e54│       │ asukasl│        │
    │        │o"      │        │        │9f2bd"  │       │uettelo │        │
    │        │        │        │        │        │       │1800-182│        │
    │        │        │        │        │        │       │0","Book│        │
    │        │        │        │        │        │       │"]]     │        │
    └────────┴────────┴────────┴────────┴────────┴───────┴────────┴────────┘
    """
    titles = ["change", "uniq_id", "id", "rname", "type", "sources", "notes"]
    repositories = []
    result = Repository.get_w_source(uniq_id)
    for record in result:
        # <Record uniq_id=138741 rname='8. Suomenmaalaisen sotilasseurakunnan arkisto'
        #    type='Library' change='1541271759' handle='_e048d8ea78c7afc76c452682e16' id='R0215'
        #    sources=[[142172, '8. M metrikka 1908-1908 (I C:1)', 'Book']]
        #    webref=[]>
        r = Repository()
        r.uniq_id = record["uniq_id"]
        r.rname = record["rname"] or ""
        r.change = record["change"]
        # r.handle = record['handle']
        r.type = record["type"] or ""
        r.id = record["id"] or ""
        for node in record["notes"]:
            n = Note.from_node(node)
            r.notes.append(n)

        for node in record["sources"]:
            s = Source()
            s.uniq_id = node[0]
            s.stitle = node[1]
            s.sauthor = node[2]
            s.spubinfo = node[3]
            s.reporef_medium = node[4]  # Todo: Should use repository.medium
            r.sources.append(s)

        repositories.append(r)

    return (titles, repositories)


def obsolete_read_same_eventday(event_type):
    """Lukee tietokannasta henkilötiedot, joilla on sama syntymäaika, näytettäväksi"""

    ids = []
    if event_type == "Birth":
        result = Person_combo.get_people_with_same_birthday()
    elif event_type == "Death":
        result = Person_combo.get_people_with_same_deathday()
    else:
        raise NotImplementedError("Only Birth and Death accepted")

    for record in result:
        # <Record
        #    id1=259451 name1=['Julius Ferdinand', '', 'Lundahl']
        #    birth1=[0, 1861880, 1861880] death1=[0, 1898523, 1898523]
        #    id2=494238 name2=['Julius Ferdinand', '', 'Lundahl']
        #    birth2=[0, 1861880, 1861880] death2=[0, 1898523, 1898523]
        # >

        uniq_id = record["id1"]
        name = record["name1"]
        b = record["birth1"]
        birth = DateRange(b)
        d = record["death1"]
        death = DateRange(d)
        l = [uniq_id, name, birth, death]

        uniq_id = record["id2"]
        name = record["name2"]
        b = record["birth2"]
        birth = DateRange(b)
        d = record["death2"]
        death = DateRange(d)
        l.extend([uniq_id, name, DateRange(birth), DateRange(death)])

        print(f"found {l[0]} {l[1]} {l[2]}, {l[3]}")
        print(f"   -- {l[4]} {l[5]} {l[6]}, {l[7]}")
        ids.append(l)

    return ids


# def read_same_deathday(uniq_id=None):
#     """ Lukee tietokannasta Person-objektit, joilla on sama kuolinaika, näytettäväksi
#     """
#
#     ids = []
#     result = Person_combo.get_people_with_same_deathday()
#     for record in result:
#         ids.append(record['ids'])
#
#     return (ids)


def obsolete_read_same_name(uniq_id=None):
    """Lukee tietokannasta Person-objektit, joilla on sama nimi, näytettäväksi"""

    result = Name.get_people_with_same_name()
    return [record["ids"] for record in result]


def obsolete_read_sources(uniq_id=None):
    """Lukee tietokannasta Source- ja Citation- objektit näytettäväksi"""

    sources = []
    try:
        result = Source.get_source_citation(uniq_id)
        # One Source, many Citations
        for record in result:
            # Record: <Record
            #    source=<Node id=243603 labels={'Source'}
            #        properties={'handle': '_e07cc43dfb33a13e25893c4a19c', 'id': 'S1371',
            #            'stitle': '1079 Akti , joka koskee Pietariin ...',
            #            'change': '1542665570'}>
            #    citations=[<Node id=246933 labels={'Citation'}
            #        properties={'handle': '_e07cc55a985217d798f0ff0df64', 'id': 'C3223',
            #        'page': '', 'dateval': '', 'change': 1542665572, 'confidence': '2'}>
            #     ]>
            s = Source.from_node(record["source"])
            for node in record["citations"]:
                c = Citation.from_node(node)
                s.citations.append(c)
            sources.append(s)
    except Exception as err:
        print("iError obsolete_read_sources: {1} {0}".format(err, uniq_id), file=stderr)

    return sources


def obsolete_read_events_wo_cites():
    """Lukee tietokannasta Event- objektit, joilta puuttuu viittaus näytettäväksi"""

    headings = []
    titles, events = Event.get_events_wo_citation()

    headings.append(_("Event list"))
    headings.append(_("Showing events without source citation"))

    return (headings, titles, events)


def obsolete_read_events_wo_place():
    """Lukee tietokannasta Event- objektit, joilta puuttuu paikka näytettäväksi"""

    headings = []
    titles, events = Event.get_events_wo_place()

    headings.append(_("Event list"))
    headings.append(_("Showing events without places"))

    return (headings, titles, events)


def obsolete_read_families():
    """Lukee tietokannasta Family- objektit näytettäväksi"""

    u_context = UserContext(user_session, current_user, request)
    # Which range of data is shown
    u_context.set_scope_from_request(request, "person_scope")
    opt = request.args.get("o", "father", type=str)
    count = request.args.get("c", 100, type=int)

    return Family_combo.get_families(o_context=u_context, opt=opt, limit=count)


def obsolete_read_people_wo_birth():
    """Lukee tietokannasta Person- objektit, joilta puuttuu syntymätapahtuma
    näytettäväksi
    """

    headings = []
    titles, people = Person_combo.get_people_wo_birth()

    headings.append(_("Event list"))
    headings.append(_("Showing persons without a birth event"))

    return (headings, titles, people)


def obsolete_read_old_people_top():
    """Lukee tietokannasta Person- objektit, joilla syntymä- ja kuolintapahtuma
    näytettäväksi
    """

    headings = []
    titles, people = Person_combo.get_old_people_top()

    sorted_people = sorted(people, key=itemgetter(7), reverse=True)
    top_of_sorted_people = [
        sorted_people[i]
        for i in range(20 if len(sorted_people) > 19 else len(sorted_people))
    ]

    headings.append(_("Event list"))
    headings.append(_("Showing oldest persons and their age"))

    return (headings, titles, top_of_sorted_people)


def obsolete_read_places():
    """Lukee tietokannasta Place- objektit näytettäväksi"""

    headings = []
    titles, events = Place_combo.get_my_places()

    headings.append(_("List of places"))
    headings.append(_("Showing places"))

    return (headings, titles, events)


# def get_source_with_events(sourceid): # -> bl.source.SourceDataStore.get_source_list
#     """ Reads a Source with events, citations and notes.


def obsolete_read_sources_wo_cites():
    """Lukee tietokannasta Source- objektit, joilta puuttuu viittaus näytettäväksi"""

    headings = []
    titles, lists = Source.get_sources_wo_citation()

    headings.append(_("Source list"))
    headings.append(_("Showing sources without source citations"))

    return (headings, titles, lists)


def obsolete_read_sources_wo_repository():
    """Lukee tietokannasta Source- objektit, joilta puuttuu arkisto näytettäväksi"""

    headings = []
    titles, lists = Source.get_sources_wo_repository()

    headings.append(_("Source list"))
    headings.append(_("Showing sources without a repository"))

    return (headings, titles, lists)


def obsolete_get_people_by_surname(surname):
    people = []
    result = Name.get_people_with_surname(surname)
    for record in result:
        p = Person_combo()
        p.uniq_id = record["uniq_id"]
        p.get_person_and_name_data_by_id()
        people.append(p)

    return people


def obsolete_get_person_data_by_id(pid):
    """Get 5 data sets:                        ---- vanhempi versio ----

    ###Obsolete? still used in
    - /compare/uniq_id=311006,315556
    - /lista/person_data/<string:uniq_id>
    - /lista/person_data/<string:uniq_id>
    """
    raise NotImplementedError(
        "models.obsolete_datareader.obsolete_get_person_data_by_id"
    )


# def get_event_participants(uniq_id): # --> bl.event.EventReader.get_event_data()
#     '''
#         Get event data and participants: Persons and Families.
#     '''
#
#     e = Event_combo()
#     e.uniq_id = uniq_id
#     e.get_event_combo()
#
#     if e.place_ref:
#         e.place = Place_combo.get_w_notes(e.place_ref[0])
#
#     parts = []
#     result = e.get_participants()
#     for record in result:
#         # <Record role='Clergy'
#         #    p=<Node id=344292 labels={'Person'}
#         #        properties={'sortname': 'Hougberg#Svensson#Carl Adolf Hougberg',
#         #            'datetype': 19, 'confidence': '', 'sex': 1, 'change': 1541582091,
#         #            'id': 'I0442', 'date2': 1884352, 'date1': 1805441,
#         #            'uuid': '3a77b72614194491a546a4360171cf29'}>
#         #    name=<Node id=344293 labels={'Name'}
#         #        properties={'firstname': 'Carl Adolf Hougberg', 'type': 'Birth Name',
#         #            'suffix': 'Svensson', 'prefix': '', 'surname': 'Hougberg',
#         #            'order': 0}
#         # >  >
#         node = record['p']
#         name_node = record['name']
#
#         if 'Person' in node.labels:
#             p = Person_combo.from_node(node)
#         elif 'Family' in node.labels:
#             p = Family_combo.from_node(node)
#         p.role = record['role']
#         if name_node:
#             name = Name.from_node(name_node)
#             p.names.append(name)
#
#         parts.append(p)
#
#     return (e, parts)


def obsolete_get_baptism_data(uniq_id):
    """
    Get event data and participants.
    """

    persons = []

    e = Event_combo()
    e.uniq_id = uniq_id
    e.get_event_combo()

    if e.place_ref:
        place = Place_combo()
        place.uniq_id = e.place_ref[0]
        place.get_w_notes(place.uniq_id)
        # Location / place data
        e.location = place.pname
        e.locid = place.uniq_id
        e.ltype = place.type

    result = e.get_baptism_data()
    for record in result:
        p = Person_as_member()
        p.uniq_id = record["person_id"]
        p.role = record["role"]
        name = record["person_names"][0]
        pname = Name()
        pname.firstname = name[0]
        pname.surname = name[1]
        p.names.append(pname)

        persons.append(p)

    return (e, persons)


# def get_families_data_by_id(uniq_id):
#     # Sivua "table_families_by_id.html" varten
#     raise(NotImplementedError, "models.datareader.get_families_data_by_id poistettu 17.5.2020")
#
#     families = []
#
#     p = Person_combo()
#     p.uniq_id = uniq_id
#     p.get_person_and_name_data_by_id()
#
#     if p.sex == SEX_MALE:
#         result = p.get_his_families_by_id()
#     else:
#         result = p.get_her_families_by_id()
#
#     for record in result:
#         f = Family_combo()
#         f.uniq_id = record['uniq_id']
#         f.get_family_data_by_id()
#
#         # Person's birth family
#         result = p.get_parentin_id()
#         for record in result:
#             pf = Family()
#             pf.uniq_id = record["family_ref"]
#             pf.get_family_data_by_id()
#
#             father = Person_combo()
#             father.uniq_id = pf.father
#             father.get_person_and_name_data_by_id()
#             f.father = father
#
#             mother = Person_combo()
#             mother.uniq_id = pf.mother
#             mother.get_person_and_name_data_by_id()
#             f.mother = mother
#
#         spouse = Person_combo()
#         if p.sex == SEX_MALE:
#             spouse.uniq_id = f.mother
#         else:
#             spouse.uniq_id = f.father
#         spouse.get_person_and_name_data_by_id()
#         f.spouse = spouse
#
#         for child_id in f.childref_hlink:
#             child = Person_combo()
#             child.uniq_id = child_id
#             child.get_person_and_name_data_by_id()
#             f.children.append(child)
#
#         families.append(f)
#
#     return (p, families)


# def get_place_with_events (loc_id): --> DBreader.get_place_with_events
#     """ Luetaan aneettuun paikkaan liittyvä hierarkia ja tapahtumat
#         Palauttaa paikkahierarkian ja (henkilö)tapahtumat muodossa
#         [Place_list, Event_table].
#
#     place_list: Lista Place-objekteja, joissa kentät
#         id      locid eli uniq_id
#         type    paikan tyyppi (Farm, Village, ...)
#         pname   paikannimi
#         parent  isäsolmun id
#
#     event_table:
#         person        person's info
#         names         list of tuples [name_type, given_name, surname]
#         etype         event type
#         edates        event date
#     """
#     place = Place_combo.get_w_notes(loc_id)
#     try:
#         place_list = Place_combo.get_place_tree(place.uniq_id)
#     except AttributeError as e:
#         traceback.print_exc()
#         flash(f"Place {loc_id} not found", 'error')
#         traceback.print_exc()
#         return None, None, None
#     except ValueError as e:
#         flash(str(e), 'error')
#         traceback.print_exc()
#         place_list = []
#
#     event_table = Place.get_place_events(place.uniq_id)
#     return (place, place_list, event_table)


def obsolete_get_note_list(uniq_id=None):
    """Lukee tietokannasta Note- objektit näytettäväksi"""
    titles, notes = Note.get_note_list(uniq_id)
    return (titles, notes)
