#   Isotammi Genealogical Service for combining multiple researchers' results.
#   Created in co-operation with the Genealogical Society of Finland.
#
#   Copyright (C) 2016-2021  Juha Mäkeläinen, Jorma Haapasalo, Kari Kujansuu,
#                            Timo Nallikari, Pekka Valta
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Created on 16.10.2020

@author: jm
"""


class CypherPerson:
    """
    Cypher clauses for Person data access.
    """

    # ----- Person node -----

    get_person_by_uid = "MATCH (p:Person) WHERE ID(p) = $uid"
    set_sortname = """
MATCH (p:Person) WHERE ID(p) = $uid
SET p.sortname=$key"""

    # ----- Person page -----

    get_person = """
MATCH (root) -[r:OWNS|PASSED]-> (p:Person {uuid:$uuid}) 
RETURN p, type(r) AS root_type, root"""

    get_names_events = """
MATCH (p:Person) -[rel:NAME|EVENT]-> (x) WHERE ID(p) = $uid
RETURN type(rel) AS rel_type, x AS node, rel.role AS role ORDER BY x.order"""

    get_families = """
MATCH (p:Person) <-[rel:CHILD|PARENT]- (f:Family) WHERE ID(p) = $uid
OPTIONAL MATCH (f) -[:EVENT]-> (fe:Event)
OPTIONAL MATCH (f) -[mr:CHILD|PARENT]-> (m:Person) -[:NAME]-> (n:Name {order:0})
OPTIONAL MATCH (m) -[:EVENT]-> (me:Event {type:"Birth"})
RETURN type(rel) AS rel_type, rel.role as role, 
    f AS family, COLLECT(DISTINCT fe) AS events, 
    COLLECT(DISTINCT [mr.role, m, n, me]) AS members
    ORDER BY family.date1"""

    get_event_places = """
MATCH (event:Event) -[:PLACE]-> (pl:Place)
    WHERE ID(event) IN $uid_list
OPTIONAL MATCH (pl) -[:NAME]-> (pn:Place_name)
OPTIONAL MATCH (pl) -[ri:IS_INSIDE]-> (pi:Place)
OPTIONAL MATCH (pi) -[:NAME]-> (pin:Place_name)
RETURN LABELS(event)[0] AS label, ID(event) AS uniq_id, 
    pl, COLLECT(DISTINCT pn) AS pnames,
    pi, COLLECT(DISTINCT pin) AS pinames"""

    get_objs_citations_notes_medias = """
MATCH (src) -[r:CITATION|NOTE|MEDIA]-> (target)
    WHERE ID(src) IN $uid_list
RETURN src, properties(r) AS r, target"""

    # Older version:
    get_objs_citation_note_media = """
MATCH (x) -[r:CITATION|NOTE|MEDIA]-> (y)
    WHERE ID(x) IN $uid_list
RETURN LABELS(x)[0] AS label, ID(x) AS uniq_id, r, y"""

    get_names = """
MATCH (n) <-[r:NAME]- (p:Person)
    where id(p) = $pid
RETURN id(p) as pid, n as name
ORDER BY name.order"""

    get_all_persons_names = """
MATCH (n)<-[r:NAME]-(p:Person)
RETURN ID(p) AS pid, n as name
ORDER BY n.order"""

    # ----- Persons listing ----

    read_approved_persons_w_events_fw_name = """
MATCH () -[:PASSED]-> (p:Person)
    WHERE p.sortname >= $start_name
WITH p //, COLLECT(DISTINCT b.user) as owners
ORDER BY p.sortname LIMIT $limit
    MATCH (p:Person) -[:NAME]-> (n:Name)
    OPTIONAL MATCH (p) -[re:EVENT]-> (e:Event)
    OPTIONAL MATCH (p) <-[:PARENT]- (f:Family) -[rf:EVENT]-> (fe:Event)
WITH p, n, re.role as role, e, f.rel_type as rel, fe //, owners
ORDER BY p.sortname, n.order
    OPTIONAL MATCH (e) -[:PLACE]-> (pl:Place)
    OPTIONAL MATCH (fe) -[:PLACE]-> (fpl:Place)
RETURN p as person, 
    COLLECT(DISTINCT n) as names, 
    COLLECT(DISTINCT [e, pl.pname, role]) + COLLECT(DISTINCT [fe, fpl.pname, rel]) AS events
    //, owners
ORDER BY person.sortname"""

    read_my_persons_w_events_fw_name = """
MATCH (prof:UserProfile) -[:HAS_ACCESS]-> (b:Batch) -[:OWNS]-> (p:Person)
    WHERE prof.username = $user AND p.sortname >= $start_name
WITH p ORDER BY p.sortname LIMIT $limit
    MATCH (p:Person) -[:NAME]-> (n:Name)
    OPTIONAL MATCH (p) -[re:EVENT]-> (e:Event)
    OPTIONAL MATCH (p) <-[:PARENT]- (f:Family) -[rf:EVENT]-> (fe:Event)
WITH p, n, re.role as role, e, f.rel_type as rel, fe  ORDER BY p.sortname, n.order
    OPTIONAL MATCH (e) -[:PLACE]-> (pl:Place)
    OPTIONAL MATCH (fe) -[:PLACE]-> (fpl:Place)
RETURN p as person, 
    COLLECT(DISTINCT n) AS names,
    COLLECT(DISTINCT [e, pl.pname, role]) + COLLECT(DISTINCT [fe, fpl.pname, rel]) AS events 
    ORDER BY person.sortname"""

    # ----- Search page -----

    _get_events_tail_w_refnames = """
 OPTIONAL MATCH (batch:Batch) -[:OWNS]-> (person)
 OPTIONAL MATCH (person) -[r:EVENT]-> (event:Event)
 OPTIONAL MATCH (event) -[:PLACE]-> (place:Place)
 OPTIONAL MATCH (person) <-[:BASENAME*0..3]- (refn:Refname)
RETURN batch.user AS user, person, 
    COLLECT(DISTINCT name) AS names,
    COLLECT(DISTINCT refn.name) AS refnames,
    COLLECT(DISTINCT [event, place.pname, r.role]) AS events"""
    _get_events_tail = """
 OPTIONAL MATCH (batch:Batch) -[:OWNS]-> (person)
 OPTIONAL MATCH (person) -[r:EVENT]-> (event:Event)
 OPTIONAL MATCH (event) -[:PLACE]-> (place:Place)
 //OPTIONAL MATCH (person) <-[:BASENAME*0..3]- (refn:Refname)
RETURN batch.user AS user, person, 
    COLLECT(DISTINCT name) AS names,
    //COLLECT(DISTINCT refn.name) AS refnames,
    COLLECT(DISTINCT [event, place.pname, r.role]) AS events"""
    _get_events_surname = """, TOUPPER(LEFT(name.surname,1)) as initial 
    ORDER BY TOUPPER(names[0].surname), names[0].firstname"""

    # With use=rule, name=name
    get_common_events_by_refname_use = (
        """
MATCH path = ( (search:Refname) -[:BASENAME*0..3 {use:$use}]- (:Refname) )
WHERE search.name STARTS WITH $name
WITH search, nodes(path) AS x UNWIND x AS rn
    MATCH (rn) -[:REFNAME {use:$use}]-> (person:Person) <-[:PASSED]- (batch)
    MATCH (person) -[:NAME]-> (name:Name {order:0})
WITH person, name"""
        + _get_events_tail
        + _get_events_surname
    )

    # With use=rule, name=name, user=user
    get_my_events_by_refname_use = (
        """
MATCH path = ( (search:Refname) -[:BASENAME*0..3]- (:Refname))
    WHERE search.name STARTS WITH $name
WITH nodes(path) AS x UNWIND x AS rn
    MATCH (rn) -[:REFNAME {use:$use}]-> (person:Person) 
          <-[:OWNS]- (:Batch {user:$user})
    MATCH (person) -[:NAME]-> (name:Name {order:0})
WITH person, name"""
        + _get_events_tail
        + _get_events_surname
    )

    get_common_events_by_years = (
        """
MATCH () -[:PASSED]-> (person:Person)
    WHERE person.death_high >= $years[0] AND person.birth_low <= $years[1]
OPTIONAL MATCH (person) -[:NAME]-> (name:Name {order:0})
WITH person, name"""
        + _get_events_tail
        + _get_events_surname
    )

    get_my_events_by_years = (
        """
MATCH (prof:UserProfile) -[:HAS_ACCESS]-> (b:Batch) -[:OWNS]-> (person:Person)
    WHERE prof.username = $user AND 
          person.death_high >= $years[0] AND person.birth_low <= $years[1]
OPTIONAL MATCH (person) -[:NAME]-> (name:Name {order:0})
WITH person, name"""
        + _get_events_tail
        + _get_events_surname
    )

    # ---- Person with Gramps handle -----

    # class models.cypher_gramps.Cypher_person_w_handle():

    create_to_batch = """
MATCH (b:Batch {id: $batch_id})
MERGE (p:Person {handle: $p_attr.handle})
MERGE (b) -[r:OWNS]-> (p)
    SET p = $p_attr
RETURN ID(p) as uniq_id"""

    link_name = """
CREATE (n:Name) SET n = $n_attr
WITH n
MATCH (p:Person {handle:$p_handle})
MERGE (p)-[r:NAME]->(n)"""

    link_event_embedded = """
MATCH (p:Person {handle: $handle}) 
CREATE (p) -[r:EVENT {role: $role}]-> (e:Event)
    SET e = $e_attr"""

    link_event = """
MATCH (p:Person {handle:$p_handle})
MATCH (e:Event  {handle:$e_handle})
MERGE (p) -[r:EVENT {role: $role}]-> (e)"""

    link_media = """
MATCH (p:Person {handle: $p_handle})
MATCH (m:Media  {handle: $m_handle})
  CREATE (p) -[r:MEDIA]-> (m)
    SET r = $r_attr"""

    # use models.gen.cypher.Cypher_name (there is no handle)

    link_citation = """
MATCH (p:Person   {handle: $p_handle})
MATCH (c:Citation {handle: $c_handle})
MERGE (p)-[r:CITATION]->(c)"""

    link_note = """
MATCH (n) WHERE n.handle=$p_handle
MATCH (m:Note)   WHERE m.handle=$n_handle
CREATE (n)-[r:NOTE]->(m)"""

    # ----- Other -----

    fetch_selected_for_lifetime_estimates = """
MATCH (p:Person) 
    WHERE id(p) IN $idlist
OPTIONAL MATCH (p)-[r:EVENT]-> (e:Event)
OPTIONAL MATCH (p) <-[:PARENT]- (fam1:Family)
OPTIONAL MATCH (fam1:Family) -[:CHILD]-> (c)
OPTIONAL MATCH (p) <-[:CHILD]- (fam2:Family) -[:PARENT]-> (parent)
OPTIONAL MATCH (fam1)-[r2:EVENT]-> (fam_event:Event)
RETURN p, id(p) as pid, 
    COLLECT(DISTINCT [e,r.role]) AS events,
    COLLECT(DISTINCT [fam_event,r2.role]) AS fam_events,
    COLLECT(DISTINCT [c,id(c)]) as children,
    COLLECT(DISTINCT [parent,id(parent)]) as parents
"""

    fetch_all_for_lifetime_estimates = """
MATCH (p:Person) 
OPTIONAL MATCH (p)-[r:EVENT]-> (e:Event)
OPTIONAL MATCH (p) <-[:PARENT]- (fam1:Family)
OPTIONAL MATCH (fam1:Family) -[:CHILD]-> (c)
OPTIONAL MATCH (p) <-[:CHILD]- (fam2:Family) -[:PARENT]-> (parent)
OPTIONAL MATCH (fam1)-[r2:EVENT]-> (fam_event:Event)
RETURN p, id(p) as pid, 
    collect(distinct [e,r.role]) AS events,
    collect(distinct [fam_event,r2.role]) AS fam_events,
    collect(distinct [c,id(c)]) as children,
    collect(distinct [parent,id(parent)]) as parents
"""

    update_lifetime_estimate = """
MATCH (p:Person) 
    WHERE id(p) = $id
SET p.birth_low = $birth_low,
    p.death_low = $death_low,
    p.birth_high = $birth_high,
    p.death_high = $death_high
"""

    get_confidences = """
MATCH (person:Person) WHERE ID(person)=$id
OPTIONAL MATCH (person) -[:EVENT]-> (event:Event) -[r:CITATION]-> (c1:Citation)
OPTIONAL MATCH (person) <-[:PARENT]- (:Family) - [:EVENT] -> (:Event) -[:CITATION]-> (c2:Citation)
RETURN person.confidence AS confidence, 
    COLLECT(c1.confidence) + COLLECT(c2.confidence) AS list"""

    set_confidence = """
MATCH (person:Person) WHERE ID(person)=$id
SET person.confidence=$confidence"""

    get_surname_list_by_username = """
match (b:Batch{user:$username}) -[:OWNS]-> (p:Person) -[:NAME]-> (n:Name) 
where n.surname <> "" and n.surname <> "N"
return n.surname as surname, count(p) as count
order by count desc
limit $count
"""

    get_surname_list_common = """
match () -[:PASSED]-> (p:Person) -[:NAME]-> (n:Name) 
where n.surname <> "" and n.surname <> "N"
return n.surname as surname, count(p) as count
order by count desc
limit $count
"""

    set_primary_name = """
match (p:Person{uuid:$uuid})  
match (p) -[:NAME]-> (n1:Name{order:0})
match (p) -[:NAME]-> (n2:Name{order:$old_order})
set n1.order = $old_order, n2.order = 0
    """

    set_name_order = """
match (n:Name) where id(n) = $uid  
set n.order = $order
    """

    set_name_type = """
match (n:Name) where id(n) = $uid  
set n.type = $nametype
return n
    """

    get_person_for_graph = """
MATCH (n:Person)
	WHERE n.uuid in $ids 
OPTIONAL MATCH (n) --> (e:Event) WHERE e.type in ["Birth", "Death"] 
RETURN ID(n) AS uniq_id, n.uuid AS uuid, n.sortname AS sortname, 
       n.sex as gender, COLLECT([e.type, e.date1/1024]) AS events"""

    get_persons_parents = """
MATCH (n:Person) <-[:CHILD]- (f:Family) -[:PARENT]-> (p:Person)
	WHERE ID(n) in $ids 
OPTIONAL MATCH (p) --> (e:Event) WHERE e.type in ["Birth", "Death"] 
RETURN ID(p) AS uniq_id, p.uuid AS uuid, p.sortname AS sortname, 
       p.sex as gender, COLLECT([e.type, e.date1/1024]) AS events"""

    get_persons_children = """
MATCH (n:Person) <-[:PARENT]- (f:Family) -[:CHILD]-> (c:Person)
	WHERE ID(n) in $ids 
OPTIONAL MATCH (c) --> (e:Event) WHERE e.type in ["Birth", "Death"] 
RETURN ID(c) AS uniq_id, c.uuid AS uuid, c.sortname AS sortname, 
       c.sex as gender, COLLECT([e.type, e.date1/1024]) AS events"""
