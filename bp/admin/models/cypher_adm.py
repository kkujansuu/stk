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
Created on 8.3.2019

@author: jm
"""


class Cypher_adm:
    " Cypher clauses for admin purposes"

    remove_all_nodes = """
MATCH (a) 
WITH a LIMIT $limit
DETACH DELETE a"""

    remove_data_nodes = """
MATCH (a) 
WHERE NOT ( 'UserProfile' IN labels(a)
    OR 'Allowed_email' IN labels(a)
    OR 'User' IN labels(a)
    OR 'Role' IN labels(a)
    OR 'Lock' IN labels(a)
    OR 'Syslog' IN labels(a) )
WITH  a LIMIT $limit
DETACH DELETE a"""

    remove_my_nodes = """
MATCH (u:UserProfile) -[*]-> (a) WHERE u.username=$user
WITH a LIMIT $limit
DETACH DELETE a"""

    user_profile_register = """
CREATE (up:UserProfile {   
    name: $name,
    email: $email,
    username: $username,
    language: $language,
    research_years: $research_years,
    software: $software,
    researched_names: $researched_names,
    researched_places: $researched_places,
    text_message: $text_message,
    created_at: timestamp() } )"""

    user_profile_update = """
MATCH (up:UserProfile) WHERE up.email = $email 
    SET up.name = $name,
        up.email = $email,
        up.username = $username,
        up.language = $language,
        up.GSF_membership = $GSF_membership,
        up.research_years = $research_years,
        up.software = $software,
        up.researched_names = $researched_names,
        up.researched_places = $researched_places,
        up.text_message = $text_message
RETURN up"""

    #     user_profile_add = '''
    # MATCH (u:User)
    #     WHERE u.email = $email
    # CREATE (up:UserProfile {
    #         username: $username,
    #         numSessions: 0,
    #         lastSessionTime: timestamp() }
    #     ) <-[:SUPPLEMENTED]- (u)'''

    user_profile_add = """         
MATCH (u:User) 
    WHERE u.email = $email
MERGE (p:UserProfile {email: u.email})    
  ON CREATE SET p.name = u.name, p.username = u.username, p.language = u.language, p.created_at = timestamp(), p.agreed_at = $agreed_at 
  ON MATCH SET p.language = u.language, p.username = u.username
CREATE (u) -[:SUPPLEMENTED]-> (p)"""

    user_profiles_get = """
MATCH (p:UserProfile)
RETURN DISTINCT p 
    ORDER BY p.created_at DESC"""

    user_update = """
MATCH (user:User {email: $email})
SET user.name = $name,
    user.language = $language,
    user.is_active = $is_active,
    user.roles = $roles
RETURN user"""

    user_update_language = """
MATCH (user:User)
    WHERE user.username = $username
SET 
    user.language = $language
RETURN user"""

    user_role_add = """         
MATCH  (r:Role) WHERE r.name = $name
MATCH  (u:User) WHERE u.email = $email
CREATE (u) -[:HAS_ROLE]-> (r)"""

    user_role_delete = """
MATCH (u:User {email: $email}) -[c:HAS_ROLE]-> (r:Role {name: $name})
DELETE c"""

    # Access management

    list_accesses = """
MATCH (user:User) -[:SUPPLEMENTED]-> (userprofile:UserProfile)
    -[r:HAS_ACCESS]-> (batch:Batch)
WITH user, userprofile, batch, id(r) as rel_id
    OPTIONAL MATCH (batch) -[ow:OWNS]-> ()
RETURN user, userprofile, batch, rel_id, count(ow) AS cnt
    LIMIT 200"""

    add_access = """
MATCH (user:UserProfile{username:$username}), (batch:Batch{id:$batchid})
MERGE (user)-[r:HAS_ACCESS]->(batch)
RETURN r,id(r) as rel_id
"""

    delete_accesses = """
MATCH (a) -[r:HAS_ACCESS]->(b) WHERE id(r) in $idlist DELETE r
"""

    drop_empty_batches = """
MATCH (a:Batch) 
    WHERE NOT ((a)-[:OWNS]->()) AND NOT a.id CONTAINS $today
DETACH DELETE a
RETURN COUNT(a) AS cnt"""
