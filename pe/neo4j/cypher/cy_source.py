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
Created on 5.3.2020

@author: jm
"""


class CypherSource:
    """Cypher clauses for Source data access."""

    # ------------------------ Cypher fragments ------------------------

    # Select Source from auditted data / researcher's own data
    _match_auditted = "MATCH (s:Source) <-[owner:PASSED]- ()"
    _match_my_access = """MATCH (s:Source) <-[owner:OWNS]- (b:Batch) 
        <-[:HAS_ACCESS]- (u:UserProfile {username:$user})"""
    #   _match_my_own = "MATCH (s:Source) <-[owner:OWNS|OWNS_OTHER]- ()"

    _sets = """
WITH type(owner) as owner_type, s
    OPTIONAL MATCH (s) -[:NOTE]-> (note)
    OPTIONAL MATCH (s) -[r:REPOSITORY]-> (rep:Repository)
    OPTIONAL MATCH (c:Citation) -[:SOURCE]-> (s)
    OPTIONAL MATCH (c) <-[:CITATION]- (citator)
RETURN owner_type, s as source, collect(DISTINCT note) as notes, 
       collect(DISTINCT [r.medium, rep]) as repositories,
       COUNT(c) AS cit_cnt, COUNT(citator) AS ref_cnt 
ORDER BY toUpper(s.stitle)"""

    _set_selections = """
        WHERE s.stitle CONTAINS $key1 OR s.stitle CONTAINS $key2 
WITH type(owner) as owner_type, s ORDER BY toUpper(s.stitle)
    OPTIONAL MATCH (s) -[:NOTE]-> (note)
    OPTIONAL MATCH (s) -[r:REPOSITORY]-> (rep:Repository)
    OPTIONAL MATCH (c:Citation) -[:SOURCE]-> (s)
    OPTIONAL MATCH (c) <-[:CITATION]- (citator)
RETURN owner_type, s as source, collect(DISTINCT note) as notes, 
       collect(DISTINCT [r.medium, rep]) as repositories,
       COUNT(c) AS cit_cnt, COUNT(citator) AS ref_cnt 
ORDER BY toUpper(s.stitle)"""

    _single_set_selection = """
        WHERE s.uuid=$uuid
WITH s, owner
    OPTIONAL MATCH (s) -[r:REPOSITORY]-> (rep:Repository)
    OPTIONAL MATCH (s) -[:NOTE]-> (n)
RETURN type(owner) as owner_type, s AS source, 
    COLLECT(DISTINCT n) AS notes,
    COLLECT(DISTINCT [r.medium,rep]) AS reps
    ORDER BY source.stitle"""

    get_citators_of_source = """
match (s) <-[:SOURCE]- (c:Citation) where id(s)=$uniq_id
match (c) <-[:CITATION]- (x)
with c,x
    optional match (c) -[:NOTE]-> (n:Note)
    optional match (x) <-[re:EVENT|NAME|MEDIA]- (pe)
return c as citation, collect(distinct n) as notes, x as near,
    collect(distinct [pe, re.role]) as far
order by c.id, x.id"""

    # ------------------------ Cypher clauses ------------------------

    get_auditted_sets = _match_auditted + _sets
    get_own_sets = _match_my_access + _sets

    get_auditted_set_selections = _match_auditted + _set_selections
    get_own_set_selections = _match_my_access + _set_selections

    get_auditted_set_single_selection = _match_auditted + _single_set_selection
    get_own_set_single_selection = _match_my_access + _single_set_selection

    # Default name, birth and death
    get_person_lifedata = """
match (p:Person) -[:NAME]-> (n:Name {order:0})
    where id(p) = $pid
optional match (p) -[re:EVENT]-> (e:Event)
    where e.type = "Birth" or e.type = "Death"
return n as name, collect(distinct e) as events"""

    #     get_citation_sources_repositories = """
    # MATCH (c:Citation) -[:SOURCE]-> (s:Source)
    #     WHERE ID(c) IN $uid_list
    #     OPTIONAL MATCH (s) -[rel:REPOSITORY]-> (r:Repository)
    # RETURN LABELS(c)[0] AS label, ID(c) AS uniq_id, s, rel, r"""

    get_citation_sources_repositories = """
MATCH (cita:Citation) -[:SOURCE]-> (source:Source)
    WHERE ID(cita) IN $uid_list
OPTIONAL MATCH (source) -[rel:REPOSITORY]-> (repo:Repository)
RETURN ID(cita) AS uniq_id, source, properties(rel) as rel, repo"""
