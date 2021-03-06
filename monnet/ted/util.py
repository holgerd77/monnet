from lxml import etree
from glob import iglob
from pprint import pprint
from sqlalchemy import func, select, and_

from monnet.util import engine, walk_path

documents_table = engine['ted_documents']
contracts_table = engine['ted_contracts']
references_table = engine['ted_references']
cpvs_table = engine['ted_cpvs']


def ted_documents():
    for file_name in walk_path('ted/xml/'):
        if not file_name.endswith('.xml'):
            continue
        with open(file_name, 'r') as fh:
            yield file_name, fh.read()


def ted_contracts():
    contract_alias = contracts_table.table.alias('contract')
    document_alias = documents_table.table.alias('document')
    _tables = [contract_alias, document_alias]
    _filters = and_(contract_alias.c.doc_no == document_alias.c.doc_no)


    q = select(_tables, _filters, _tables, use_labels=True,
               order_by=[document_alias.c.doc_no.desc()])
    for contract in engine.query(q):
        yield contract


class Extractor(object):

    def __init__(self, el):
        self.el = el
        self.paths = {}
        self._ignore = set()
        self.generate(el)

    def element_name(self, el):
        if el == self.el:
            return '.'
        return self.element_name(el.getparent()) + '/' + el.tag

    def generate(self, el):
        children = el.getchildren()
        if len(children):
            for child in children:
                self.generate(child)
        else:
            name = self.element_name(el)
            if not name in self.paths:
                self.paths[name] = el

    def ignore(self, path):
        if path.endswith('*'):
            path = path[:len(path)-1]
            for p in self.paths.keys():
                if p.startswith(path):
                    self._ignore.add(p)
        else:
            self._ignore.add(path)

    def text(self, path, ignore=True):
        if path is None:
            return
        el = self.el.find(path)
        if el is None:
            return None
        if ignore:
            self.ignore(self.element_name(el))
        return el.text

    def html(self, path, ignore=True):
        if path is None:
            return
        el = self.el.find(path)
        if el is None:
            return None
        if ignore:
            self.ignore(self.element_name(el))
        return etree.tostring(el)

    def attr(self, path, attr, ignore=True):
        if path is None:
            return
        el = self.el.find(path)
        if el is None:
            return None
        if ignore:
            self.ignore(self.element_name(el))
        return el.get(attr)

    def audit(self):
        #print "UNPARSED:"
        for k, v in sorted(self.paths.items()):
            if k in self._ignore:
                continue
            if v.text or len(v.attrib.keys()):
                pprint({
                    'path': k,
                    'text': v.text,
                    'attr': v.attrib
                })


