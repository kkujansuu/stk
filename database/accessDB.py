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

# coding: utf-8

# from datetime import datetime
import logging

logger = logging.getLogger("stkserver")

# from neobolt.exceptions import ConstraintError # Obsolete
from neo4j.exceptions import ClientError, ConstraintError  # ,CypherSyntaxError
from flask_security import utils as sec_utils

import shareds
from .cypher_setup import SetupCypher
from .schema_fixes import do_schema_fixes

# All User roles here:
ROLES = (
    {
        "level": "0",
        "name": "guest",
        "description": "Rekisteröitymätön käyttäjä, näkee esittelysukupuun",
    },
    {
        "level": "1",
        "name": "gedcom",
        "description": "Kirjautunut käyttäjä, pääsee vain gedcom-muunnoksiin",
    },
    {
        "level": "2",
        "name": "member",
        "description": "Seuran jäsen täysin lukuoikeuksin",
    },
    {
        "level": "4",
        "name": "research",
        "description": "Tutkija, joka voi käsitellä omaa tarjokasaineistoaan",
    },
    {
        "level": "8",
        "name": "audit",
        "description": "Valvoja, joka auditoi ja hyväksyy gramps- ja tarjokasaineistoja",
    },
    {"level": "16", "name": "admin", "description": "Ylläpitäjä kaikin oikeuksin"},
    {
        "level": "32",
        "name": "master",
        "description": "Tietokannan pääkäyttäjä, ei sovellusoikeuksia",
    },
    {
        "level": "-1",
        "name": "to_be_approved",
        "description": "Käyttäjä joka odottaa hyväksymistä",
    },
)

# ====== Database schema ======
# increment this, if shcema must be updated
DB_SCHEMA_VERSION = "2021.1.0"
# =============================


# def get_dataservice(opt="update"):
#     ''' Returns a data service of selected type.
#
#         :param: opt    service selection
#             "read"     Neo4jReadService
#             "read_tx"  Neo4jReadServiceTx
#             "update"   Neo4jDataService
#     '''
#     service = shareds.dataservices[opt]
#     return service(shareds.driver)


def initialize_db():
    """
    Check and initiate important nodes and constraints and schema fixes,
    if (:Lock{id:'initiated'}) schema is not == database.accessDB.DB_SCHEMA_VERSION.

    The database connection has been established in
    pe.neo4j.neo4jengine.Neo4jEngine called from app.setups.py

    """
    if schema_updated():
        return

    logger.info(
        "database.accessDB.initialize_db: checking roles, constraints "
        f"and schema fixes (version {DB_SCHEMA_VERSION})"
    )

    if not roles_exist():
        create_role_constraints()
        create_roles()

    if not user_exists("master"):
        create_user_constraints()
        create_master_user()

    if not user_exists("guest"):
        create_guest_user()

    if not profile_exists("_Stk_"):
        create_single_profile("_Stk_")

    create_lock_w_constraint()

    create_year_indexes()

    constr_list = {
        "Citation": {"uuid"},
        "Event": {"uuid"},
        "Family": {"uuid"},
        "Media": {"uuid"},
        "Note": {"uuid"},
        "Person": {"uuid"},
        "Place": {"uuid"},
        "Repository": {"uuid"},
        "Role": {"name"},
        "Source": {"uuid"},
        "User": {"email", "username"},
    }
    check_constraints(constr_list)

    # Fix changed schema
    do_schema_fixes()


# --------------  Database Administration -------------


def delete_database(tx):
    # erase total database
    tx.run(SetupCypher.delete_database)


def schema_updated():
    # Check, that Lock 'initiated' exists and schema is updated.
    result = shareds.driver.session().run(SetupCypher.check_lock_initiated)
    active_version = 0
    for record in result:
        active_version = record[0]
    return active_version == DB_SCHEMA_VERSION


def roles_exist():
    #  Tarkista roolien olemassaolo
    print(f"Check there exist all {len(ROLES)} user roles")
    results = shareds.driver.session().run(SetupCypher.check_role_count)
    roles_found = [result[0] for result in results]
    for i in ROLES:
        if i["name"] not in roles_found:
            print(f'role {i.get("name")} not found')
            return False
    return True


def role_exists(name):
    # print(f'Check the existense of the {name} role')
    num_of_roles = 0
    for result in shareds.driver.session().run(
        SetupCypher.role_check_existence, rolename=name
    ):
        num_of_roles = result[0]
    return num_of_roles > 0


def create_role(tx, role):
    try:
        tx.run(
            SetupCypher.role_create,
            level=role["level"],
            name=role["name"],
            description=role["description"],
        )
        print(f'Role {role["name"]} created')
    except ClientError as e:
        # print(f'Role {role["name"]} exists')
        return
    except Exception as e:
        logging.error(f"database.accessDB.create_role: {e.__class__.__name__}, {e}")
        raise


def create_roles():
    with shareds.driver.session() as session:
        for role in ROLES:
            create_role(session, role)

        print("Roles initialized")


def user_exists(name):
    print(f"Check the existense of the {name} user")
    num_of_users = 0
    for result in shareds.driver.session().run(
        SetupCypher.user_check_existence, username=name
    ):
        num_of_users = result[0]
    return num_of_users > 0


def profile_exists(name):
    print(f"Check the existense of {name} profile")
    num_of_users = 0
    for result in shareds.driver.session().run(
        SetupCypher.profile_check_existence, username=name
    ):
        num_of_users = result[0]
    return num_of_users > 0


def build_master_user():
    with shareds.app.app_context():
        return {
            "username": "master",
            "password": sec_utils.hash_password(
                shareds.app.config["MASTER_USER_PASSWORD"]
            ),
            "email": shareds.app.config["MASTER_USER_EMAIL"],
            "name": "Stk-kannan pääkäyttäjä",
            "language": "fi",
            "is_active": True,
            #'confirmed_at': datetime.now().timestamp()/1000,
            "roles": ["master"],
            #'last_login_at': datetime.now().timestamp()/1000,
            #'current_login_at': datetime.now().timestamp()/1000,
            "last_login_ip": "127.0.0.1",
            "current_login_ip": "127.0.0.1",
            "login_count": 0,
        }


def create_master_user():
    master_user = build_master_user()
    with shareds.driver.session() as session:
        try:
            session.run(SetupCypher.master_create, master_user)
        except Exception as e:
            logging.error(
                f"database.accessDB.create_master_user: {e.__class__.__name__}, {e}"
            )
            return
    logger.info("Master user account created")


def build_guest_user():
    with shareds.app.app_context():
        return shareds.user_model(
            username="guest",
            password=sec_utils.hash_password(shareds.app.config["GUEST_USER_PASSWORD"]),
            email=shareds.app.config["GUEST_USER_EMAIL"],
            name="Vieraileva käyttäjä",
            language="fi",
            is_active=True,
            # confirmed_at = datetime.now().timestamp()*1000,
            roles=["guest"],
            # last_login_at = datetime.now().timestamp()*1000,
            # current_login_at = datetime.now().timestamp()*1000,
            last_login_ip="127.0.0.1",
            current_login_ip="127.0.0.1",
            login_count=0,
        )


def create_guest_user():
    guest = build_guest_user()
    user = shareds.user_datastore.put(guest)
    if user:
        logger.info("Guest user account created")
    else:
        logger.error("Guest user account not created")


def create_single_profile(name):
    """Create the profile, where approved Audit nodes shall be connected.

    There is no User node for this UserProfile.
    """
    attr = {"numSessions": 0, "lastSessionTime": 0, "username": name}
    with shareds.driver.session() as session:
        try:
            session.run(SetupCypher.single_profile_create, attr=attr)
        except Exception as e:
            logger.error(
                "database.accessDB.create_single_profile"
                f" Failed {e.__class__.__name__} {e.message}"
            )
            return
    logger.info(f"Profile {name} created")


def create_role_constraints():
    with shareds.driver.session() as session:
        try:
            session.run(SetupCypher.set_role_constraint)
        except ClientError as e:
            msgs = e.message.split(",")
            print(f"Role constraint ok: {msgs[0]}")
            return
        except Exception as e:
            logging.error(
                f"database.accessDB.create_role_constraints: {e.__class__.__name__}, {e}"
            )
            return
    logger.info("Role constraints created")


def create_user_constraints():
    """Unique contraint for User email and user properties"""
    cnt = 0
    with shareds.driver.session() as session:
        for query in [
            SetupCypher.set_user_constraint1,
            SetupCypher.set_user_constraint2,
        ]:
            try:
                session.run(query)
                cnt += 1
            except ConstraintError:  # print(f'User constraint ok')
                pass
            except ClientError:  # print(f'User constraint seems to be ok')
                pass
            except Exception as e:
                logging.error(
                    f"database.accessDB.create_user_constraints: {e.__class__.__name__}, {e}"
                )
                return
    if cnt:
        logger.info(f"{cnt} User constraints created")
    else:
        print(f"User constraint ok")


def create_year_indexes():
    """Person node is indexed by two year properties."""
    cnt = 0
    with shareds.driver.session() as session:
        for query in [
            SetupCypher.index_year_birth_low,
            SetupCypher.index_year_death_high,
        ]:
            try:
                session.run(query)
                cnt += 1
            except ConstraintError:  # print(f'Person years index ok')
                pass
            except ClientError:  # print(f'Person years seems to be ok')
                pass
            except Exception as e:
                msgs = e.message.split(",")
                print(
                    f"database.accessDB.create_year_indexes: {e.__class__.__name__}, {msgs[0]}"
                )
                return
    if cnt:
        logger.info(f"{cnt} Person years indexes created")
    else:
        print(f"Person years indexes ok")


def check_constraints(needed: dict):
    # Create missing UNIQUE constraints from given nodes and parameters.

    for label, props in needed.items():
        for prop in props:
            create_unique_constraint(label, prop)
    #     print(f'checked {n_ok} constraints ok')
    return


def create_lock_w_constraint():
    # Initial lock with schema version.
    with shareds.driver.session() as session:
        # Create first Lock node and contraint
        session.run(
            SetupCypher.update_lock,
            id="initiated",
            db_schema=DB_SCHEMA_VERSION,
            locked=False,
        )
        print(f"Initial Lock (version {DB_SCHEMA_VERSION}) created")
        create_unique_constraint("Lock", "id")
        return


def re_initiate_nodes_constraints_fixes():
    # Remove initial lock for re-creating nodes, constraints and schema fixes
    with shareds.driver.session() as session:
        session.run(SetupCypher.remove_lock_initiated)
        logger.info(f"database.accessDB.re_initiate_nodes_constraints_fixes: requested")
        print("Initial Lock removed")
        return


def create_unique_constraint(label, prop):
    " Create given contraint for given label and property."
    with shareds.driver.session() as session:
        query = f"create constraint on (n:{label}) assert n.{prop} is unique"
        try:
            session.run(query)
            print(f"Unique constraint for {label}.{prop} created")
        except ClientError as e:
            msgs = e.message.split(",")
            print(f"Unique constraint for {label}.{prop} ok: {msgs[0]}")
            return
        except Exception as e:
            logger.error(
                f"database.accessDB.create_unique_constraint: {e.__class__.__name__} {e}"
            )
            raise
    return


def create_constraint(label, prop):
    " Create given contraint for given label and property."
    with shareds.driver.session() as session:
        query = f"create constraint on (n:{label})"
        try:
            session.run(query)
            print(f"Constraint for {label}.{prop} created")
        except ClientError as e:
            msgs = e.message.split(",")
            print(f"Constraint for {label}.{prop} ok: {msgs[0]}")
            return
        except Exception as e:
            logger.error(
                f"database.accessDB.create_constraint: {e.__class__.__name__} {e}"
            )
            raise
    return
