"""Opening-cluster uncertainty; never convert an unbracketed ladder into a rating."""
from collections import Counter, defaultdict
import random
import statistics


def score(game):
    if game['result'] == '1/2-1/2': return .5
    if game['result'] not in ('1-0', '0-1'): raise ValueError('Unfinished game has no score')
    return float((game['result'] == '1-0') == (game['chessai_color'] == 'white'))


def percentile(values, fraction):
    values = sorted(values)
    index = (len(values)-1)*fraction
    lo = int(index)
    return values[lo] + (values[min(lo+1, len(values)-1)]-values[lo])*(index-lo)


def crossing(levels, scores):
    if len(levels) < 2: return None, 'At least two opponent levels are required'
    if any(b > a for a, b in zip(scores, scores[1:])):
        return None, 'Non-monotone scores: ladder is too noisy for interpolation'
    if min(scores) > .5: return None, 'No 50% bracket: ChessAI scores above 50% at every tested level'
    if max(scores) < .5: return None, 'No 50% bracket: ChessAI scores below 50% at every tested level'
    equal = [elo for elo, value in zip(levels, scores) if value == .5]
    if len(equal) > 1: return None, 'A 50% plateau does not identify a unique crossing'
    if equal: return equal[0], None
    for a, b, sa, sb in zip(levels, levels[1:], scores, scores[1:]):
        if sa > .5 > sb: return a + (b-a)*(sa-.5)/(sa-sb), None
    return None, 'No unique 50% crossing'


def summary(games, seed, iterations=5000, infer=True):
    completed = [g for g in games if g.get('result') in ('1-0', '0-1', '1/2-1/2')]
    by_level = defaultdict(list)
    for game in completed: by_level[game['opponent_elo']].append(game)
    result = {'levels': {}, 'calibration': {'estimate': None, 'ci95': None, 'reason': 'Incomplete or invalid run; inference withheld'}}
    clusters = {}
    for elo, group in sorted(by_level.items()):
        values = [score(g) for g in group]
        entry = {'games': len(group), 'wins': values.count(1), 'draws': values.count(.5), 'losses': values.count(0),
                 'score_percent': 100*statistics.mean(values), 'average_plies': statistics.mean(g['plies'] for g in group),
                 'termination_counts': dict(Counter(g['termination'] for g in group)), 'by_color': {}, 'score_ci95_percent': None}
        for color in ('white', 'black'):
            sample = [score(g) for g in group if g['chessai_color'] == color]
            entry['by_color'][color] = {'games': len(sample), 'wins': sample.count(1), 'draws': sample.count(.5),
                                        'losses': sample.count(0), 'score_percent': 100*statistics.mean(sample) if sample else None}
        paired = defaultdict(list)
        for g in group: paired[g['opening_id']].append(g)
        clusters[elo] = paired
        entry['opening_clusters'] = len(paired)
        result['levels'][str(elo)] = entry
    if not infer or not by_level: return result
    levels = sorted(by_level)
    ids = sorted(clusters[levels[0]])
    if any(set(clusters[elo]) != set(ids) for elo in levels):
        raise ValueError('Ladder must use the same opening clusters at every level')
    matrix = {}
    for elo in levels:
        for pair in clusters[elo].values():
            if len(pair) != 2 or {g['chessai_color'] for g in pair} != {'white', 'black'}:
                raise ValueError('Each opening cluster must contain exactly one game per color')
        matrix[elo] = [statistics.mean(score(g) for g in clusters[elo][opening]) for opening in ids]
    if len(ids) < 2:
        result['calibration']['reason'] = 'Fewer than two independent opening clusters; no uncertainty estimate'
        return result
    rng = random.Random(seed)
    samples = {elo: [] for elo in levels}
    estimates = []
    for _ in range(iterations):
        # The SAME sampled opening IDs across all opponent levels preserve cross-level dependence.
        indices = [rng.randrange(len(ids)) for _ in ids]
        scores = [statistics.mean(matrix[elo][i] for i in indices) for elo in levels]
        for elo, value in zip(levels, scores): samples[elo].append(value)
        estimate, _ = crossing(levels, scores)
        if estimate is not None: estimates.append(estimate)
    for elo in levels:
        result['levels'][str(elo)]['score_ci95_percent'] = [100*percentile(samples[elo], p) for p in (.025, .975)]
    point, reason = crossing(levels, [statistics.mean(matrix[elo]) for elo in levels])
    identified = len(estimates)/iterations
    result['calibration'] = {'estimate': None, 'ci95': None, 'method': 'linear interpolation of monotone score ladder at 50%',
                             'bootstrap_unit': 'opening, both colors, jointly across levels',
                             'bootstrap_iterations': iterations, 'bootstrap_identified_fraction': identified,
                             'observed_crossing': point, 'reason': reason}
    if point is not None and identified >= .95 and len(ids) >= 2:
        # Failed/unbracketed replicates occupy both extreme tails conservatively.
        failed = iterations-len(estimates)
        ordered = sorted(estimates)
        lower_rank = int(.025*(iterations-1))-failed
        upper_rank = int(.975*(iterations-1))
        if lower_rank >= 0 and upper_rank < len(ordered):
            result['calibration'].update(estimate=point, ci95=[ordered[lower_rank], ordered[upper_rank]], reason=None)
        else:
            result['calibration']['reason'] = 'Bootstrap uncertainty includes unbracketed/noisy ladders; finite 95% interval not identified'
    elif point is not None:
        result['calibration']['reason'] = 'Insufficient independent clusters or unstable 50% bracket; no reliable calibrated estimate'
    return result
