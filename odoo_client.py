import xmlrpc.client
from config import *

# Authenticate
common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")

uid = common.authenticate(
    ODOO_DB,
    ODOO_USERNAME,
    ODOO_API_KEY,
    {}
)

if not uid:
    raise Exception("Odoo Authentication Failed ❌")

models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")


def execute(model, method, args=None, kwargs=None):
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    return models.execute_kw(
        ODOO_DB,
        uid,
        ODOO_API_KEY,
        model,
        method,
        args,
        kwargs
    )