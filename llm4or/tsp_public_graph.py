"""Development-only public TSP graph candidate extractor.

This accepts only an internally complete undirected pair table. It does not
decide whether the prose truly specifies symmetric TSP or solve a tour.
"""

from decimal import Decimal, InvalidOperation
import hashlib
import re


class TspPublicGraphError(ValueError):
    pass


SCHEMA = 'tsp-public-graph-candidate-v1'
_PAIR = re.compile(
    r'\*[ \t]*(?P<left>[^:\n]{1,80}?)\s+to\s+'
    r'(?P<right>[^:\n]{1,80}?)\s*:\s*'
    r'(?P<weight>[0-9]+(?:\.[0-9]+)?)\s+'
    r'(?P<unit>[A-Za-z-]+)[ \t]*', re.I)
_UNITS = {'minute': 'minutes', 'minutes': 'minutes', 'min': 'minutes',
          'meter': 'meters', 'meters': 'meters', 'km': 'km', 'ms': 'ms'}


def _label(value: str) -> str:
    return ' '.join(value.strip().split())


def _candidate_graph(edges: list[dict], expected_nodes: int,
                     prefix: str | None) -> tuple[list[str], list[dict]] | None:
    pairs = set()
    out = []
    nodes = set()
    for edge in edges:
        labels = []
        for raw in (edge['left'], edge['right']):
            label = raw[len(prefix) + 1:] if prefix and raw.startswith(prefix + ' ') else raw
            labels.append(label)
            nodes.add(label)
        pair = tuple(sorted(labels))
        if pair[0] == pair[1] or pair in pairs:
            return None
        pairs.add(pair)
        out.append({'nodes': list(pair), 'weight': edge['weight'],
                    'evidence': edge['evidence']})
    if len(nodes) != expected_nodes or len(pairs) != expected_nodes * (expected_nodes - 1) // 2:
        return None
    return sorted(nodes), out


def extract_tsp_public_graph(text: str, expected_nodes: int) -> dict:
    if type(text) is not str or type(expected_nodes) is not int \
            or not 4 <= expected_nodes <= 19:
        raise TspPublicGraphError('input_scope')
    try:
        encoded = text.encode('utf-8')
    except UnicodeError as exc:
        raise TspPublicGraphError('input_encoding') from exc
    if not 0 < len(encoded) <= 30_000:
        raise TspPublicGraphError('input_scope')
    parsed = []
    offset = 0
    units = set()
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith('*'):
            match = _PAIR.fullmatch(stripped)
            if match is None:
                raise TspPublicGraphError('malformed_bullet')
            left, right = _label(match['left']), _label(match['right'])
            if not left or not right:
                raise TspPublicGraphError('malformed_bullet')
            token = match['weight']
            if '.' in token and len(token.split('.')[1]) > 3:
                raise TspPublicGraphError('weight_precision')
            try:
                value = Decimal(token)
            except InvalidOperation as exc:
                raise TspPublicGraphError('malformed_bullet') from exc
            if not 0 < value <= 1_000_000_000:
                raise TspPublicGraphError('weight_range')
            unit = _UNITS.get(match['unit'].casefold())
            if unit is None:
                raise TspPublicGraphError('unsupported_unit')
            units.add(unit)
            start = offset + line.index('*')
            quote = line[line.index('*'):].strip()
            parsed.append({'left': left, 'right': right, 'weight': str(value),
                           'evidence': {'start': start, 'end': start + len(quote),
                                        'quote': quote}})
        elif _PAIR.fullmatch('* ' + stripped) is not None:
            raise TspPublicGraphError('unlisted_pair')
        offset += len(line)
    if len(parsed) != expected_nodes * (expected_nodes - 1) // 2:
        raise TspPublicGraphError('pair_count')
    if len(units) != 1:
        raise TspPublicGraphError('unit_conflict')
    raw_labels = {edge[side] for edge in parsed for side in ('left', 'right')}
    exact = _candidate_graph(parsed, expected_nodes, None)
    if exact is not None:
        nodes, edges = exact
        policy = 'exact'
    else:
        prefixes = sorted({label.split(' ', 1)[0] for label in raw_labels if ' ' in label})
        candidates = [(prefix, graph) for prefix in prefixes
                      if (graph := _candidate_graph(parsed, expected_nodes, prefix)) is not None]
        if not candidates:
            raise TspPublicGraphError('node_or_pair_inventory')
        if len(candidates) != 1:
            raise TspPublicGraphError('ambiguous_alias')
        policy, (nodes, edges) = candidates[0]
    return {'schema': SCHEMA, 'question_sha256': hashlib.sha256(encoded).hexdigest(),
            'expected_nodes': expected_nodes, 'nodes': nodes, 'edges': edges,
            'unit': next(iter(units)), 'alias_policy': policy,
            'semantics_validated': False, 'solver_called': False}


__all__ = ['SCHEMA', 'TspPublicGraphError', 'extract_tsp_public_graph']
