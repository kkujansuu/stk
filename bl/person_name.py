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

    Person Name class

Created on 10.9.2018

@author: jpek@iki.fi
"""
from sys import stderr
import logging

logger = logging.getLogger("stkserver")

import shareds
from bl.base import NodeObject

# Todo: move to pe.neo4j
from models.gen.cypher import Cypher_name


class Name(NodeObject):
    """Person name.

    Properties:
            type                str Name type: 'Birth name', ...
            order               int name order of Person etc. (from Gramps xml)
            firstname           str etunimi
            surname             str sukunimi
            prefix              str etuliite
            suffix              str patronyme / patronyymi
            title               str titteli, esim. Sir, Dr.
            citation_handles[]  str gramps handles for citations
            citation_ref[]      int uniq_ids of citation nodes
    """

    def __init__(self, givn="", surn="", pref="", suff="", titl=""):
        """ Luo uuden name-instanssin """
        self.type = ""
        self.order = None
        self.firstname = givn
        self.surname = surn
        self.prefix = pref
        self.suffix = suff
        self.title = titl
        # For gramps xml?
        self.citation_handles = []
        # For person page
        self.citation_ref = []

    def __str__(self):
        # Gedcom style key
        return "{} /{}/{}/{}/{}".format(
            self.title, self.firstname, self.prefix, self.surname, self.suffix
        )

    def key_surname(self):
        # Standard sort order key "Klick#Brita Helena#Jönsdotter"
        return f"{self.surname}#{self.firstname}#{self.suffix}"

    @classmethod
    def from_node(cls, node):
        """
        Transforms a db node to an object of type Name

        <Node id=80308 labels={'Name'}
            properties={'title': 'Sir', 'firstname': 'Brita Helena', 'suffix': '', 'order': 0,
                'surname': 'Klick', '': 'Birth Name'}>
        """
        n = cls()
        n.uniq_id = node.id
        # n.id = node.id    # Name has no id "N0000"
        n.type = node["type"]
        n.firstname = node.get("firstname", "")
        n.prefix = node.get("prefix", "")
        n.suffix = node.get("suffix", "")
        n.title = node.get("title", "")
        n.surname = node.get("surname", "")
        n.order = node["order"]
        return n

    def save(self, tx, **kwargs):    # parent_id=None):
        """Creates or updates this Name node. (There is no handle)
        If parent_id is given, a link (parent) -[:NAME]-> (Name) is created

        #TODO: Check, if this name exists; then update or create new
        """
        if "parent_id" not in kwargs:
            raise ValueError("Name.save: no base person defined")

        try:
            n_attr = {
                "order": self.order,
                "type": self.type,
                "firstname": self.firstname,
                "surname": self.surname,
                "prefix": self.prefix,
                "suffix": self.suffix,
                "title": self.title,
            }
            tx.run(
                Cypher_name.create_as_leaf,
                n_attr=n_attr,
                parent_id=kwargs["parent_id"],
                citation_handles=self.citation_handles,
            )
        except ConnectionError as err:
            raise SystemExit("Stopped in Name.save: {}".format(err))
        except Exception as err:
            print("iError (Name.save): {0}".format(err), file=stderr)

    @staticmethod
    def get_people_with_same_name():
        """ Etsi kaikki henkilöt, joiden nimi on sama"""

        query = """
            MATCH (p1:Person)-[r1:NAME]->(n1:Name)
            MATCH (p2:Person)-[r2:NAME]->(n2:Name) WHERE ID(p1)<ID(p2)
                AND n2.surname = n1.surname AND n2.firstname = n1.firstname
                RETURN COLLECT ([ID(p1), p1.est_birth, p1.est_death,
                n1.firstname, n1.suffix, n1.title, n1.surname,
                ID(p2), p2.est_birth, p2.est_death,
                n2.firstname, n2.suffix, n2.title, n2.surname]) AS ids
            """.format()
        return shareds.driver.session().run(query)

    @staticmethod
    def get_people_with_surname(surname):
        """ Etsi kaikki henkilöt, joiden sukunimi on annettu"""

        query = """
            MATCH (p:Person)-[r:NAME]->(n:Name) WHERE n.surname='{}'
                RETURN DISTINCT ID(p) AS uniq_id
            """.format(
            surname
        )
        return shareds.driver.session().run(query)

    @staticmethod
    def get_clearname(uniq_id=None):
        """Lists all Name versions of this Person as single cleartext"""
        result = Name.get_personnames(None, uniq_id)
        names = []
        for record in result:
            # <Node id=210189 labels={'Name'}
            #    properties={'title': 'Sir', 'firstname': 'Jan Erik', 'type': 'Birth Name',
            #        'suffix': 'Jansson', 'surname': 'Mannerheim', 'order': 0}>
            node = record["name"]
            fn = node.get("firstname", "")
            vn = node.get("prefix", "")
            sn = node.get("surname", "")
            pn = node.get("suffix", "")
            ti = node.get("title", "")
            names.append("{} {} {} {} {}".format(ti, fn, pn, vn, sn))
        return " • ".join(names)

    #     @staticmethod
    #     def get_personnames(tx=None, uniq_id=None):
    #         """ Picks all Name versions of this Person or all persons.
    #
    #             Use optionally refnames or sortname for person selection
    #         """
    #         if not tx:
    #             tx = shareds.driver.session()
    #
    #         if uniq_id:
    #             result = tx.run(Cypher_person.get_names, pid=uniq_id)
    #         else:
    #             result = tx.run(Cypher_person.get_all_persons_names)
    #
    #         names = []
    #         for record in result:
    #             # <Record
    #             #    pid=82
    #             #    name=<Node id=83 labels=frozenset({'Name'})
    #             #        properties={'title': 'Sir', 'firstname': 'Jan Erik', 'surname': 'Mannerheimo',
    #             #            'prefix': '', 'suffix': 'Jansson', 'type': 'Birth Name', 'order': 0}
    #             # >  >
    #             node = record['name']
    #             name = Name.from_node(node)
    #             name.person_uid =  record['pid']
    #             names.append(name)
    #         return names

    @staticmethod
    def get_surnames():
        """ Listaa kaikki sukunimet tietokannassa """

        query = """
            MATCH (n:Name) RETURN distinct n.surname AS surname
                ORDER BY n.surname
            """
        return shareds.driver.session().run(query)
