import random
from collections import Counter

import pytest

from red_black_numbers import Cell, Norm, calculate_metrics, make_board, target_sequence


def test_sequences_match_method():
    first = target_sequence(1)
    assert first[:6] == [Cell(1, "black"), Cell(17, "red"), Cell(2, "black"),
                         Cell(16, "red"), Cell(3, "black"), Cell(15, "red")]
    assert len(first) == 34
    assert len(target_sequence(2)) == 51
    assert target_sequence(2)[2] == Cell(1, "white_red")
    assert len(target_sequence(3)) == 68
    assert target_sequence(3)[3] == Cell(17, "white_black")


def test_board_sizes_and_contents():
    for stage, size in ((1, 36), (2, 64), (3, 81)):
        board = make_board(stage, random.Random(42))
        assert len(board) == size
        assert sorted((c.kind, c.number) for c in board if c) == sorted((c.kind, c.number) for c in target_sequence(stage))


def test_metrics_and_error_floor():
    m = calculate_metrics([2.0, 2.0], 2, [1.0], 1, Norm(1.0, 4, 1.0, 2))
    assert m["mean_cycle"] == 2.0
    assert m["table_pace"] == 0.25
    assert m["range_table_pace"] == 0.5
    assert m["interference_index"] == 2.0
    assert calculate_metrics([1], 99, [1], 99, Norm())["table_pace"] == 0.0


@pytest.mark.parametrize('stage,kinds,side,blank_count', [
    (1, ('black','red'), 6, 2),
    (2, ('black','red','white_red'), 8, 13),
    (3, ('black','red','white_red','white_black'), 9, 13),
])
def test_complete_ranges_and_terminal_pair(stage,kinds,side,blank_count):
    sequence=target_sequence(stage)
    assert len(sequence)==17*len(kinds)
    for kind in kinds:
        assert sorted(c.number for c in sequence if c.kind==kind)==list(range(1,18))
    assert sequence[-len(kinds):]==[Cell(17 if k in ('black','white_red') else 1,k) for k in kinds]
    board=make_board(stage,random.Random(89))
    assert len(board)==side*side and board.count(None)==blank_count
    assert Counter(c for c in board if c)==Counter(sequence)


@pytest.mark.parametrize('stage,side', [(1,6),(2,8),(3,9)])
def test_random_layouts_are_varied_and_spatially_mixed(stage,side):
    layouts=[];blank_positions=set()
    for seed in range(60):
        board=make_board(stage,random.Random(seed))
        layouts.append(tuple(board))
        blank_positions.update(i for i,c in enumerate(board) if c is None)
        first,second=board.index(Cell(1,'black')),board.index(Cell(17,'red'))
        assert max(abs(first//side-second//side),abs(first%side-second%side))>1
        if stage==1:
            a,b=[i for i,c in enumerate(board) if c is None]
            assert max(abs(a//side-b//side),abs(a%side-b%side))>1
        for kind in {c.kind for c in board if c}:
            positions=[i for i,c in enumerate(board) if c and c.kind==kind]
            expected=17*(side//2)/side
            assert abs(sum(i//side<side//2 for i in positions)-expected)<=3
            assert abs(sum(i%side<side//2 for i in positions)-expected)<=3
        for category in (
            [None if c is None else c.kind in ('red','white_red') for c in board],
            [None if c is None else c.number<=8 for c in board],
        ):
            for row in range(side):
                for col in range(side):
                    for height,width in ((1,5),(5,1),(3,3)):
                        if row+height<=side and col+width<=side:
                            values=[category[(row+y)*side+col+x] for y in range(height) for x in range(width)]
                            assert values[0] is None or len(set(values))>1
    assert len(set(layouts))==60
    assert len(blank_positions)>side*side*.8
    assert make_board(stage,random.Random(123))==make_board(stage,random.Random(123))
