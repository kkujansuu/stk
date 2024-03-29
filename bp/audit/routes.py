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
Created on 28.11.2019

 Auditor operations page urls
 
"""
from . import bp
import time

import logging
from io import StringIO, BytesIO
import csv

logger = logging.getLogger("stkserver")

from flask import render_template, request, redirect, url_for
from flask import send_file
from flask_security import login_required, roles_accepted, current_user
from flask_babelex import _
import gettext

import shareds
from bl.audit import Audit
from bl.batch import Batch
from bl.person import Person, PersonBl
from bl.refname import Refname
from bp.admin.cvs_refnames import load_refnames
from .models.batch_merge import Batch_merge

from bp.admin import uploads
from models import syslog, loadfile, dbutil


@bp.route("/audit")
@login_required
@roles_accepted("audit")
def audit_home():
    return render_template("/audit/index.html")


# ------------------------- User Gramps uploads --------------------------------


@bp.route("/audit/list_uploads", methods=["GET"])
@login_required
@roles_accepted("audit")
def list_uploads():
    """Show Batches

    The list of Gramps uploads is filtered by an existing Batch node
    """
    users = shareds.user_datastore.get_users()
    upload_list = list(uploads.list_uploads_all(users))
    logger.info(f"-> bp.audit.routes.list_uploads")
    return render_template("/audit/batches.html", uploads=upload_list)


# --------------------- Move Batch to Approved data ----------------------------


@bp.route("/audit/movein/<batch_name>", methods=["GET", "POST"])
@login_required
@roles_accepted("audit")
def move_in_1(batch_name):
    """ Confirm Batch move to Isotammi database """
    user, batch_id, tstring, labels = Batch.get_batch_stats(batch_name)
    total = sum(cnt for _label, cnt in labels)
    # Not needed: logger.info(f' bp.audit.routes.move_in_1 {user} / {batch_name}, total {total} nodes')

    return render_template(
        "/audit/move_in_1.html",
        user=user,
        batch=batch_id,
        label_nodes=labels,
        total=total,
        time=tstring,
    )


@bp.route("/audit/movenow", methods=["POST"])
@login_required
@roles_accepted("audit")
def move_in_2():
    """ Move the accepted Batch to Isotammi database """
    owner = request.form["user"]
    batch_id = request.form["batch"]
    auditor = current_user.username
    logger.info(f" bp.audit.routes.move_in_2 u={owner} b={batch_id}")
    merger = Batch_merge()
    msg = merger.move_whole_batch(batch_id, owner, auditor)
    syslog.log(type="batch to Common data", batch=batch_id, by=owner, msg=msg)
    return redirect(url_for("audit.move_in_1", batch_name=batch_id))


# --------------------- Delete an approved data batch ----------------------------


@bp.route("/audit/batch_delete/<batch_id>", methods=["POST"])
@login_required
@roles_accepted("audit")
def delete_approved(batch_id):
    """Confirm approved batch delete"""
    (msg, nodes_deleted) = Audit.delete_audit(current_user.username, batch_id)
    if msg != "":
        logger.error(f"{msg}")
    else:
        logger.info(f'-> bp.audit.routes.batch_delete f="{batch_id}"')
        syslog.log(type="approved batch_id deleted", batch_id=batch_id)

    referrer = request.headers.get("Referer")
    return redirect(referrer)


# --------------------- List Approved data batches ----------------------------


@bp.route("/audit/approvals/<who>", methods=["GET", "POST"])
@login_required
@roles_accepted("audit")
def audit_approvals(who=None):
    """ List Audit batches """
    t0 = time.time()
    auditor = None if who == "all" else current_user.username
    titles, batches = Audit.get_auditor_stats(auditor)
    # {'matti/2020-01-03.001/13.01.2020 20:30': {'Note': 17, 'Place': 30, 'Repository': 3},
    #  'teppo/2020-01-03.002/23.01.2020 15:52': {...} ...}
    total = 0
    for key in batches.keys():
        # print(key + ":")
        for _lbl, cnt in batches[key].items():
            # print (f'    {_lbl} = {cnt}')
            total += cnt
    logger.info(
        f" bp.audit.routes.audit_approvals {auditor} {len(batches)} batches, total {total} nodes"
    )

    return render_template(
        "/audit/approvals.html",
        user=auditor,
        total=total,
        titles=titles,
        batches=batches,
        elapsed=time.time() - t0,
    )


# --------------------- List classifiers and refnames ----------------------------


@bp.route("/audit/classifiers", methods=["GET"])
@login_required
def list_classifiers():
    # List classifier values and translations
    import ui.jinja_filters

    # Translation is not possible, the original search kay is not known
    # sv = gettext.translation('messages', 'app/translations', languages=['sv'])
    # en = gettext.translation('messages', 'app/translations', languages=['en'])

    key_dicts = ui.jinja_filters.list_translations()
    data = {}
    n = 0
    rows_lt = {}
    for key, values in key_dicts.items():
        # key: 'nt'
        # values: ('Name types', {'Aatelointinimi': 'aateloitu nimi',  ...})
        rows = []
        desc = values[0]
        todo = True
        for term, value in values[1].items():
            if key == "lt_in":
                # Put 'lt_in' value to last column of 'lt' row
                for row in rows_lt:
                    if row[0] == term:
                        row[2] = value
                        todo = False
                        break
                if todo:
                    rows_lt.append([term, " ", value])
            else:
                row = [term, value, ""]
                rows.append(row)
        n += len(values[1])
        data[key] = (desc, rows)
        if key == "lt":
            rows_lt = rows
    # >>> data['marr']
    # ('marriage types', [['Married', 'Avioliitossa', ''], ['Unknown', ...]])

    logger.info(f"-> bp.audit.routes.list_classifiers n={n}")
    return render_template("/audit/classifiers.html", data=data)


# Refnames home page
@bp.route("/audit/refnames")
@login_required
@roles_accepted("audit")
def refnames():
    """ Operations for reference names """
    return render_template("/audit/reference.html")


@bp.route("/audit/set/refnames")
@login_required
@roles_accepted("member", "admin", "audit")
def set_all_person_refnames():
    """ Setting reference names for all persons """
    dburi = dbutil.get_server_location()
    (refname_count, _sortname_count) = PersonBl.set_person_name_properties(
        ops=["refname"]
    ) or _("Done")
    logger.info(f"-> bp.audit.routes.set_all_person_refnames n={refname_count}")
    return render_template(
        "/talletettu.html",
        uri=dburi,
        text=f"Updated {_sortname_count} person sortnames, {refname_count} refnames",
    )


@bp.route("/audit/download/refnames")
@login_required
@roles_accepted("audit")
def download_refnames():
    """Download reference names as a CSV file"""
    logger.info(f"-> bp.audit.routes.download_refnames")  # n={refname_count}")
    with StringIO() as f:
        writer = csv.writer(f)
        hdrs = "Name,Refname,Reftype,Gender,Source,Note".split(",")
        writer.writerow(hdrs)
        # refnames = datareader.read_refnames()
        refnames = Refname.get_refnames()
        for refname in refnames:
            row = [
                refname.name,
                refname.refname,
                refname.reftype,
                Person.convert_sex_to_str(refname.sex),
                refname.source,
            ]
            writer.writerow(row)
        csvdata = f.getvalue()
        f2 = BytesIO(csvdata.encode("utf-8"))
        f2.seek(0)
        return send_file(
            f2,
            mimetype="text/csv",
            as_attachment=True,
            attachment_filename="refnames.csv",
        )


@bp.route("/audit/upload_csv", methods=["POST"])
@login_required
@roles_accepted("audit")
def upload_csv():
    """Load a cvs file to temp directory for processing in the server"""
    try:
        infile = request.files["filenm"]
        material = request.form["material"]
        logging.info(f"-> bp.audit.routes.upload_csv/{material} f='{infile.filename}'")

        loadfile.upload_file(infile)
        if "destroy" in request.form and request.form["destroy"] == "all":
            logger.info("-> bp.audit.routes.upload_csv/delete_all_Refnames")
            # datareader.recreate_refnames()
            Refname.recreate_refnames()

    except Exception as e:
        return redirect(url_for("virhesivu", code=1, text=str(e)))

    return redirect(
        url_for("audit.save_loaded_csv", filename=infile.filename, subj=material)
    )


@bp.route("/audit/save/<string:subj>/<string:filename>")
@login_required
@roles_accepted("audit")
def save_loaded_csv(filename, subj):
    """ Save loaded cvs data to the database """
    pathname = loadfile.fullname(filename)
    dburi = dbutil.get_server_location()
    logging.info(f"-> bp.audit.routes.save_loaded_csv/{subj} f='{filename}'")
    try:
        if subj == "refnames":  # Stores Refname objects
            status = load_refnames(pathname)
        else:
            return redirect(
                url_for(
                    "virhesivu",
                    code=1,
                    text=_("Data type '{}' is not supported").format(subj),
                )
            )
    except KeyError as e:
        return render_template(
            "virhe_lataus.html",
            code=1,
            text=_("Missing proper column title: ") + str(e),
        )
    return render_template("/talletettu.html", text=status, uri=dburi)
