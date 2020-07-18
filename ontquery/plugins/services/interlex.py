from typing import Union, List, Dict

import rdflib
import requests

import ontquery as oq
import ontquery.exceptions as exc
from ontquery.utils import cullNone, log, QueryResult
from ontquery.services import OntService
from .interlex_client import InterLexClient
from .rdflib import rdflibLocal
from . import deco


class _InterLexSharedCache:
    _graph_cache = {}
    # FIXME maxsize ??


@deco.ilx_host
@deco.ilx_port
class InterLexRemote(_InterLexSharedCache, OntService):  # note to self
    known_inverses = ('', ''),
    defaultEndpoint = 'https://scicrunch.org/api/1/'
    def __init__(self, *args, apiEndpoint=defaultEndpoint,
                 user_curies: dict={'ILX', 'http://uri.interlex.org/base/ilx_'},  # FIXME hardcoded
                 readonly=False,
                 OntId=oq.OntId,
                 **kwargs):
        """ user_curies is a local curie mapping from prefix to a uri
            This usually is a full http://uri.interlex.org/base/ilx_1234567 identifier """

        self.OntId = OntId
        self.apiEndpoint = apiEndpoint

        self.user_curies = user_curies
        self.readonly = readonly

        self.Graph = rdflib.Graph
        self.RDF = rdflib.RDF
        self.OWL = rdflib.OWL
        self.URIRef = rdflib.URIRef
        #self.curies = requests.get(f'http://{self.host}:{self.port}/base/curies').json()  # FIXME TODO
        # here we see that the original model for curies doesn't quite hold up
        # we need to accept local curies, but we also have to have them
        # probably best to let the user populate their curies from interlex
        # at the start, rather than having it be completely wild
        # FIXME can't do this at the moment because interlex itself calls this --- WHOOPS
        super().__init__(*args, **kwargs)

    def setup(self, **kwargs):
        oq.OntCuries({'ILXTEMP':'http://uri.interlex.org/base/tmp_'})

        if self.apiEndpoint is not None:
            try:
                self.ilx_cli = InterLexClient(base_url=self.apiEndpoint)
            except InterLexClient.NoApiKeyError:
                if not self.readonly:
                    # expect attribute errors for ilx_cli
                    log.warning('You have not set an API key for the SciCrunch API! '
                                'InterLexRemote will error if you try to use it.')

        super().setup(**kwargs)

    @property
    def host_port(self):
        return f'{self.host}:{self.port}' if self.port else self.host

    @property
    def predicates(self):
        return {}  # TODO

    def add_class(self,
                  label: str = None,
                  definition: str = None,
                  synonyms: tuple = tuple(),
                  comment: str = None,
                  cid: Union[str, int] = None,
                  subClassOf: str = None,
                  predicates: dict = None) -> QueryResult:
        return self.add_entity(
            type='term',
            label=label,
            definition=definition,
            synonyms=synonyms,
            comment=comment,
            cid=cid,
            subThingOf=subClassOf,
            predicates=predicates,
        )

    def add_pde(self,
                label,
                definition: str = None,
                synonyms: tuple = tuple(),
                comment: str = None,
                predicates: dict = None,
                subThingOf: str = None,
                cid: Union[str, int] = None,
                existing_ids: list = None,) -> QueryResult:
        """ add a personal data element """
        return self.add_entity(
            type='pde',
            cid=cid,
            subThingOf=subThingOf,
            label=label,
            definition=definition,
            synonyms=synonyms,
            comment=comment,
            predicates=predicates,
            existing_ids=existing_ids,
        )

    def add_cde(self,
                label: str,
                definition: str = None,
                synonyms: tuple = tuple(),
                comment: str = None,
                cid: Union[str, int] = None,
                predicates: dict = None,
                subThingOf: str = None,
                existing_ids: list = None,) -> QueryResult:
        """ add a common data element """
        return self.add_entity(
            type='cde',
            cid=cid,
            subThingOf=subThingOf,
            label=label,
            definition=definition,
            synonyms=synonyms,
            comment=comment,
            predicates=predicates,
            existing_ids=existing_ids,
        )

    def add_fde(self,
                label,
                definition: str = None,
                synonyms: tuple = tuple(),
                comment: str = None,
                cid: Union[str, int] = None,
                predicates: dict = None,
                subThingOf: str = None,
                existing_ids: list = None,) -> QueryResult:
        """ add a federated data element """
        return self.add_entity(
            type='fde',
            cid=cid,
            subThingOf=subThingOf,
            label=label,
            definition=definition,
            synonyms=synonyms,
            comment=comment,
            predicates=predicates,
            existing_ids=existing_ids,
        )

    def add_predicates(self, ilx_curieoriri: str, predicate_objects_dict: dict) -> list:
        tresp = []
        if not ilx_curieoriri.startswith('http://uri.interlex.org/base/'):  # FIXME: need formality
            subject = 'http://uri.interlex.org/base/' + ilx_curieoriri
        else:
            subject = ilx_curieoriri
        for predicate, objs in predicate_objects_dict.items():
            if not isinstance(objs, list):
                objs = [objs]
            for object in objs:
                # server output doesnt include their ILX IDs ... so it's not worth getting
                tresp.append(self.add_triple(subject, predicate, object))
                # TODO stick the responding predicates etc in if success
        return tresp

    def delete_predicates(self, ilx_curieoriri: str, predicate_objects_dict: dict) -> list:
        tresp = []
        if not ilx_curieoriri.startswith('http://uri.interlex.org/base/'):  # FIXME: need formality
            subject = 'http://uri.interlex.org/base/' + ilx_curieoriri
        else:
            subject = ilx_curieoriri
        for predicate, objs in predicate_objects_dict.items():
            if not isinstance(objs, list):
                objs = [objs]
            for object in objs:
                # server output doesnt include their ILX IDs ... so it's not worth getting
                tresp.append(self.delete_triple(subject, predicate, object))
                # TODO stick the responding predicates etc in if success
        return tresp

    def get_entity(self, ilx_id: str) -> dict:
        resp = self.ilx_cli.get_entity(ilx_id)
        return self.QueryResult(
            query_args=kwargs,
            iri='http://uri.interlex.org/base/' + resp['ilx'],
            curie=resp['ilx'].replace('ilx_', 'ILX:').replace('tmp_', 'TMP:'),
            label=resp['label'],
            labels=tuple(),
            # abbrev=None, # TODO
            # acronym=None, # TODO
            definition=resp['definition'],
            synonyms=tuple(resp['synonyms']),
            # deprecated=None,
            # prefix=None,
            # category=None,
            predicates={p: tuple() for p in predicates},  # TODO
            # _graph=None,
            source=self,
        )

    def add_entity(self,
                   label: str,
                   type: str,
                   subThingOf: str,
                   definition: str = None,
                   comment: str = None,
                   cid: Union[str, int] = None,
                   synonyms: tuple = tuple(),
                   existing_ids: List[dict] = None,
                   predicates: dict = None,) -> QueryResult:
        """ Add InterLex entity

        :param label: Preferred name of entity.
        :param type: Any of the following: term, TermSet, cde, pde, fde, relationship, annotation.
        :param cid: Community ID
        :param definition: Entities official definition.
        :param comment: A foot note regarding either the interpretation of the data or the data itself
        :param subThingOf: The ilx_id of the parent of this entity. Example: Organ is a superclass to Brain
        :param synonyms: Alternate names of the label.
        :param existing_ids: Alternate/source ontological iri/curies. Can only be one preferred ID.
        :param predicates: Anotations or Relationships associated with enitty.
        :return: requests.Response of insert or query from existing.
        """
        if self.readonly:
            raise exc.ReadOnlyError('InterLexRemote is in readonly mode.')

        resp = self.ilx_cli.add_entity(
            label=label,
            type=type,
            definition=definition,
            comment=comment,
            synonyms=synonyms,
            cid=cid,
            superclass=subThingOf,
            existing_ids=existing_ids,
        )
        out_predicates = {}

        if predicates:
            tresp = self.add_predicates(ilx_curieoriri=resp['ilx'], predicate_objects_dict=predicates)
            resp['annotations'] = tresp # TODO: Creates a record for annotations in term_versions table

        if 'comment' in resp:  # filtering of missing fields is done in the client
            out_predicates['comment'] = resp['comment']

        return QueryResult(
            query_args={},
            iri='http://uri.interlex.org/base/' + resp['ilx'],
            curie=resp['ilx'].replace('ilx_', 'ILX:').replace('tmp_', 'TMP:'),
            label=resp['label'],
            labels=tuple(),
            # abbrev=None,  # TODO
            # acronym=None,  # TODO
            definition=resp.get('definition', None),
            synonyms=tuple(resp.get('synonyms', tuple())),
            # deprecated=None,
            # prefix=None,
            # category=None,
            predicates=out_predicates,
            # _graph=None,
            source=self,
        )

    def update_entity(self,
                      ilx_id: str = None,
                      label: str = None,
                      type: str = None,
                      definition: str = None,
                      subThingOf: str = None,
                      comment: str = None,
                      add_synonyms: tuple = None,
                      delete_synonyms: tuple = None,
                      add_existing_ids: List[dict] = None,
                      delete_existing_ids: List[dict] = None,
                      predicates_to_add: dict = None,
                      predicates_to_delete: dict = None,
                      cid: str = None) -> object:
        """ Update existing entity.

        :param ilx_id:
        :param label:
        :param type:
        :param definition:
        :param subThingOf:
        :param comment:
        :param add_synonyms:
        :param delete_synonyms:
        :param add_existing_ids: iris and curies to be added to entity.
        :param delete_existing_ids: iris and curies to be deleted from entity.
        :param predicates_to_add:
        :param predicates_to_delete:
        :param cid:
        :return: QueryResult of entity record
        """
        resp = self.ilx_cli.update_entity(
            ilx_id=ilx_id,
            label=label,
            type=type,
            superclass=subThingOf,
            definition=definition,
            comment=comment,
            add_synonyms=add_synonyms,
            delete_synonyms=delete_synonyms,
            add_existing_ids=add_existing_ids,
            delete_existing_ids=delete_existing_ids,
            cid=cid,
            # predicates=tresp,
        )

        tresp = None
        if predicates_to_add:
            trep = self.add_predicates(ilx_curieoriri=resp['ilx'], predicate_objects_dict=predicates_to_add)

        tresp = None
        if predicates_to_delete:
            trep = self.delete_predicates(ilx_curieoriri=resp['ilx'], predicate_objects_dict=predicates_to_delete)

        out_predicates = {}
        if 'comment' in resp:  # filtering of missing fields is done in the client
            out_predicates['comment'] = resp['comment']
        result = QueryResult(
             query_args={},
             iri='http://uri.interlex.org/base/' + resp['ilx'],
             curie=resp['ilx'].replace('ilx_', 'ILX:').replace('tmp_', 'TMP:'),
             label=resp['label'],
             labels=tuple(),
             # abbrev=None, # TODO
             # acronym=None, # TODO
             definition=resp['definition'],
             synonyms=tuple([d['literal'] for d in resp['synonyms']]),
             # deprecated=None,
             # prefix=None,
             # category=None,
             predicates=out_predicates,
             # _graph=None,
             source=self,
        )
        return result

    def add_triple(self, subject, predicate, object):
        """ Triple of curied or full iris to add to graph.
            Subject should be an interlex"""

        def filter_ontid(ontid):
            if ontid.startswith('http://'):
                pass
            elif ontid.prefix == 'ILXTEMP':
                ontid = 'tmp_' + ontid.suffix
            else:
                ontid = 'ilx_' + ontid.suffix
            return ontid

        # this split between annotations and relationships is severely annoying
        # because you have to know before hand which one it is (sigh)
        s = self.OntId(subject)
        p = self.OntId(predicate)
        o = self._get_type(object)
        if type(o) == str:
            func = self.ilx_cli.add_annotation
        elif type(o) == self.OntId:
            func = self.ilx_cli.add_relationship
            o = filter_ontid(o)
        else:
            raise TypeError(f'what are you giving me?! {object!r}')

        s = filter_ontid(s)
        p = filter_ontid(p)

        resp = func(s, p, o)
        return resp

    def delete_triple(self, subject, predicate, object):
        """ Triple of curied or full iris to add to graph.
            Subject should be an interlex"""

        def filter_ontid(ontid):
            if ontid.startswith('http://'):
                pass
            elif ontid.prefix == 'ILXTEMP':
                ontid = 'tmp_' + ontid.suffix
            else:
                ontid = 'ilx_' + ontid.suffix
            return ontid

        # this split between annotations and relationships is severely annoying
        # because you have to know before hand which one it is (sigh)
        s = self.OntId(subject)
        p = self.OntId(predicate)
        o = self._get_type(object)
        if type(o) == str:
            func = self.ilx_cli.delete_annotation
        elif type(o) == self.OntId:
            func = self.ilx_cli.delete_relationship
            o = filter_ontid(o)
        else:
            raise TypeError(f'what are you giving me?! {object!r}')

        s = filter_ontid(s)
        p = filter_ontid(p)

        # TODO: check if add_relationship works
        resp = func(s, p, o)
        return resp

    def _get_type(self, entity):
        try:
            return self.OntId(entity)
        except self.OntId.Error:
            return entity

    @property
    def _is_dev_endpoint(self):
        return bool(self.port)

    def query(self, iri=None, curie=None, label=None, term=None, predicates=tuple(),
              prefix=tuple(), exclude_prefix=tuple(), limit=10, **_):
        kwargs = cullNone(iri=iri, curie=curie, label=label, term=term, predicates=predicates)
        if iri:
            oiri = self.OntId(iri=iri)
            icurie = oiri.curie
            if curie and icurie and icurie != curie:
                raise ValueError(f'curie and curied iri do not match {curie} {icurie}')
            else:
                curie = icurie

        elif curie:
            iri = self.OntId(curie).iri

        if self._is_dev_endpoint:
            res = self._dev_query(kwargs, iri, curie, label, predicates, prefix, exclude_prefix)
            if res is not None:
                yield res

        elif hasattr(self, 'ilx_cli'):
            res = self._scicrunch_api_query(
                kwargs=kwargs,
                iri=iri,
                curie=curie,
                label=label,
                term=term,
                predicates=predicates,
                limit=limit)

            yield from res

        else:  # can only get by iri directly and it must be an ilx id
            # if label:
            #     raise NotImplementedError('can only query by label on the dev endpoint or with an API key set')

            res = self._dev_query(kwargs, iri, curie, label, predicates, prefix, exclude_prefix)
            if res is not None:
                yield res

    def _scicrunch_api_query(self, kwargs, iri, curie, label, term, predicates, limit):
        if iri:
            resps: dict = self.ilx_cli.get_entity(iri)
        elif curie:
            resps: dict = self.ilx_cli.get_entity(curie)
        elif label:
            resps: list = self.ilx_cli.query_elastic(label=label, size=limit)
        elif term:
            resps: list = self.ilx_cli.query_elastic(term=term, size=limit)
        else:
            return

        if not resps:
            return
        elif isinstance(resps, dict):
            resps = [resps]

        for resp in resps:
            yield QueryResult(
                query_args = kwargs,
                iri='http://uri.interlex.org/base/' + resp['ilx'],
                curie=resp['ilx'].replace('ilx_', 'ILX:').replace('tmp_', 'TMP:'),
                label=resp['label'],
                labels=tuple(),
                #abbrev=None, # TODO
                #acronym=None, # TODO
                definition=resp['definition'],
                synonyms=tuple(resp['synonyms']),
                #deprecated=None,
                #prefix=None,
                #category=None,
                predicates={p:tuple() for p in predicates},  # TODO
                #_graph=None,
                source=self,
            )

    def _dev_query(self, kwargs, iri, curie, label, predicates, prefix, exclude_prefix):
        def get(url, headers={'Accept':'application/n-triples'}):  # FIXME extremely slow?
            with requests.Session() as s:
                s.headers.update(headers)
                resp = s.get(url, allow_redirects=False)
                while resp.is_redirect and resp.status_code < 400:  # FIXME redirect loop issue
                    # using send means that our headers don't show up in every request
                    resp = s.get(resp.next.url, allow_redirects=False)
                    if not resp.is_redirect:
                        break
            return resp

        class NoOnt(Exception): pass
        class NoAbout(Exception): pass

        def isAbout(g):
            try:
                ontid, *r1 = g[:self.RDF.type:self.OWL.Ontology]
            except ValueError as e:
                raise NoOnt('oops!') from e

            try:
                o, *r2 = g[ontid:self.URIRef('http://purl.obolibrary.org/obo/IAO_0000136')]
            except ValueError as e:
                raise NoAbout('oops!') from e

            if r1 or r2:
                raise ValueError(f'NonUnique value for ontology {r1} or about {r2}')

            return o

        if curie:
            if curie.startswith('ILX:') and iri:
                # FIXME hack, can replace once the new resolver is up
                url = iri.replace('uri.interlex.org', self.host_port)
            else:
                url = f'http://{self.host_port}/base/curies/{curie}?local=True'
        elif label:
            url = f'http://{self.host_port}/base/lexical/{label}'
        else:
            return None

        if url in self._graph_cache:
            graph = self._graph_cache[url]
            if not graph:
                return None
        else:
            resp = get(url)
            if not resp.ok:
                self._graph_cache[url] = None
                return None
            ttl = resp.content
            if ttl.startswith(b'<!DOCTYPE HTML PUBLIC'):
                return None  # FIXME disambiguation multi results page

            graph = self.Graph().parse(data=ttl, format='turtle')
            self._graph_cache[url] = graph

        try:
            ia_iri = isAbout(graph)
        except NoOnt as e:
            # almost certainly an old interlex format
            log.exception(e)
            return None
        except NoAbout as e:
            # almost certainly an old interlex format
            log.exception(e)
            return None

        i = self.OntId(ia_iri)
        if exclude_prefix and i.prefix in exclude_prefix:
            return None

        if prefix and i.prefix not in prefix:  # FIXME alternate ids ...
            return None

        rdll = rdflibLocal(graph)
        rdll.setup(instrumented=self.OntTerm)

        if True:
            #qrs = rdll.query(label=label, predicates=predicates, all_classes=True)  # label=label issue?
            qrs = rdll.query(predicates=predicates, all_classes=True)
            qrd = {'predicates': {}}  # FIXME iri can be none?
            toskip = 'predicates',
            if curie is None and iri is None:
                #i = OntId(ia_iri)
                qrd['curie'] = i.curie
                qrd['iri'] = i.iri
                toskip += 'curie', 'iri'
            else:
                qrd['predicates']['TEMP:preferredId'] = i,  # FIXME this should probably be in the record itself ...

            if curie:
                qrd['curie'] = curie
                toskip += 'curie',
            if iri:
                qrd['iri'] = iri.iri if isinstance(iri, self.OntId) else iri
                toskip += 'iri',

            for qr in qrs:
                #print(tc.ltgreen(str(qr)))
                # FIXME still last one wins behavior
                n = {k:v for k, v in qr.items()
                     if k not in toskip
                     and v is not None}
                qrd.update(n)
                qrd['predicates'].update(cullNone(**qr['predicates']))

            qrd['source'] = self
            #print(tc.ltyellow(str(qrd)))
            return QueryResult(kwargs, **qrd)

    def _dev_query_rest(self):
        if True:
            pass
        else:
            # TODO cases where ilx is preferred will be troublesome
            maybe_out = [r for r in rdll.query(curie=curie, label=label, predicates=predicates)]
            if maybe_out:
                out = maybe_out
            else:
                out = rdll.query(iri=ia_iri, label=label, predicates=predicates)
                if curie:
                    for qr in out:
                        qr = cullNone(**qr)
                        yield QueryResult(kwargs, #qr._QueryResult__query_args,
                                               curie=curie,
                                               **{k:v for k, v in qr.items()
                                                  if k != 'curie' })

                    return

            yield from out
