"""
Created on 2.5.2017 from Ged-prepare/Bus/classes/genealogy.py

Changed 13.6.2018/JMä: get_notes() result from list(str) to list(Note)

@author: jm
"""

from sys import stderr

from bl.base import NodeObject
from .cypher import Cypher_note
from models.cypher_gramps import Cypher_note_in_batch  # Cypher_note_w_handle,
import shareds


class Note(NodeObject):
    """Note / Huomautus
    including eventual web link

    Properties:
            handle          str stats with '_' if comes from Gramps
            change          int timestamp from Gramps
            id              esim. "N0001"
            uniq_id         int database key
            priv            int >0 non-public information
            type            str note type
            text            str note description
            url             str web link
    """

    def __init__(self):
        """Creates a Note instance in memory"""
        NodeObject.__init__(self)
        self.type = ""
        self.priv = None
        self.text = ""
        self.url = None

    def __str__(self):
        desc = self.text if len(self.text) < 17 else self.text[:16] + "..."
        url = "" if self.url is None else self.url
        return "{} {} {!r} {}".format(self.id, self.type, desc, url)

    @classmethod
    def from_node(cls, node):
        """
        Transforms a db node to an object of type Note.
        """
        n = cls()
        n.uniq_id = node.id
        n.id = node["id"] or ""
        if "handle" in node:
            n.handle = node["handle"]
        n.change = node["change"]
        if "priv" in node:
            n.priv = node["priv"]
        n.type = node.get("type", "")
        n.text = node.get("text", "")
        n.url = node.get("url", "")
        return n

    #     @staticmethod
    #     def get_persons_notes(uniq_id):
    #         """ Read 'Person -> Event -> Note' and 'Person -> Note' paths
    #
    #             Haetaan henkilön Citationit, suoraan tai välisolmujen kautta
    #
    #             Returns list of Citations and list of Source ids
    #         ╒══════╤══════╤══════╤════════════════════════════════════════════════╕
    #         │"p_id"│"e_id"│"n_id"│"n"                                             │
    #         ╞══════╪══════╪══════╪════════════════════════════════════════════════╡
    #         │99833 │81393 │78943 │{"handle":"_dea2effe2b579e6d11c157b268c","text":│
    #         │      │      │      │"Tornion tuomiokunnan tuomari","id":"N0089","pri│
    #         │      │      │      │v":"","type":"Event Note","change":1529946203}  │
    #         ├──────┼──────┼──────┼────────────────────────────────────────────────┤
    #         │99833 │81409 │78936 │{"handle":"_dea5b1e04a32efc4f77eb368d87","text":│
    #         │      │      │      │"Kuopion tuomiokunnan 1822","id":"N2057","priv":│
    #         │      │      │      │"","type":"Event Note","change":1530020220}     │
    #         └──────┴──────┴──────┴────────────────────────────────────────────────┘
    #         """
    #
    #         result = shareds.driver.session().run(Cypher_note.get_person_notes,
    #                                               pid=uniq_id)
    #         notes = []
    #         for record in result:
    #             pass
    #
    #         return notes

    @staticmethod
    def get_notes(uniq_ids):
        """Reads Note nodes data from db using given Note uniq_ids

        Called from models.datareader.get_person_data_by_id
        """

        notes = []
        with shareds.driver.session() as session:
            result = session.run(Cypher_note.get_by_ids, nid=uniq_ids)
            for record in result:
                # Create a Note object from record
                node = record["n"]
                n = Note.from_node(node)
                notes.append(n)

        return notes

    @staticmethod
    def get_note_list(uniq_id):
        """Reads all Note nodes or selected Note node from db
        Also counts references to each Note

        Called only from models.datareader.get_notes for "table_of_data.html"
        """

        result = None
        with shareds.driver.session() as session:
            if uniq_id:
                query = """
MATCH (n:Note) WHERE ID(note)=$nid
    OPTIONAL MATCH (a) --> (n)
RETURN ID(n) AS uniq_id, n, count(a) AS ref"""
                result = session.run(query, nid=uniq_id)
            else:
                query = """
MATCH (n:Note)
    OPTIONAL MATCH (a) --> (n)
RETURN ID(n) AS uniq_id, n, count(a) AS ref 
    ORDER BY n.type"""
                result = session.run(query)

        titles = ["uniq_id", "change", "id", "priv", "type", "text", "url", "ref"]
        notes = []

        for record in result:
            # Create a Note object from record
            node = record["n"]
            n = Note.from_node(node)
            n.ref = record["ref"]
            notes.append(n)

        return (titles, notes)

    @staticmethod
    def get_total():
        """ Tulostaa huomautusten määrän tietokannassa """

        with shareds.driver.session() as session:
            results = session.run("MATCH (n:Note) RETURN COUNT(n)")
            for result in results:
                return str(result[0])
        return 0

    @staticmethod
    def save_note_list(tx, parent):
        """Save the parent.notes[] objects as a descendant of the parent node."""
        n_cnt = 0
        for note in parent.notes:
            if isinstance(note, Note):
                if not note.id:
                    n_cnt += 1
                    note.id = f"N{n_cnt}-{parent.id}"
                note.save(tx, parent_id=parent.uniq_id)
            else:
                raise AttributeError("note.save_note_list: Argument not a Note")

    def save(self, tx, **kwargs):  # batch_id=None, parent_id=None):
        """Creates this Note object as a Note node
        - if parent_id is given, link (parent) --> (:Note)
        - else if batch_id is given, link (:Batch) --> (:Note)
        """
        self.uuid = self.newUuid()
        n_attr = {}
        try:
            n_attr = {
                "uuid": self.uuid,
                "change": self.change,
                "id": self.id,
                "priv": self.priv,
                "type": self.type,
                "text": self.text,
                "url": self.url,
            }
            if self.handle:
                n_attr["handle"] = self.handle
            if "parent_id" in kwargs:
                # print(f"Note_save: parent (uid={kwargs['parent_id']}) --> (id={self.id})")
                self.uniq_id = tx.run(
                    Cypher_note_in_batch.create_as_leaf,
                    parent_id=kwargs["parent_id"],
                    n_attr=n_attr,
                ).single()[0]
            elif "batch_id" in kwargs:
                # print(f"Note_save: batch ({kwargs['batch_id']}) --> ({self.id})")
                self.uniq_id = tx.run(
                    Cypher_note_in_batch.create, bid=kwargs["batch_id"], n_attr=n_attr
                ).single()[0]
            else:
                raise RuntimeError(
                    f"Note.save needs batch_id or parent_id for {self.id}"
                )

        except Exception as err:
            print(f"iError Note_save: {err} attr={n_attr}", file=stderr)
            raise RuntimeError(f"Could not save Note {self.id}")
