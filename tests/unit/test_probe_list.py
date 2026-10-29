# ABOUTME: Checks the counting list the worker hands to a solution under a probe budget.
# ABOUTME: It must act like a list and record which positions the solution looked at.

import bisect

import pytest

from practice._worker import ProbeList

ITEMS = [-7, -3, 0, 2, 5, 8, 13, 21, 34, 55]


def fresh() -> ProbeList:
    return ProbeList(ITEMS)


def test_it_is_a_list_with_the_same_contents() -> None:
    probes = fresh()
    assert isinstance(probes, list)
    assert len(probes) == len(ITEMS)
    assert probes == ITEMS
    assert list(probes) == ITEMS
    assert probes.probe_count == len(ITEMS)  # The line above read everything.


def test_len_and_truthiness_are_free() -> None:
    probes = fresh()
    assert len(probes) == 10
    assert bool(probes) is True
    assert probes.probe_count == 0


def test_one_index_counts_one_position_however_often_it_is_read() -> None:
    probes = fresh()
    assert probes[4] == 5
    assert probes[4] == 5
    assert probes[4] < probes[4] + 1
    assert probes.probe_count == 1


def test_negative_indexes_count_the_position_they_name() -> None:
    probes = fresh()
    assert probes[-1] == 55
    assert probes[9] == 55
    assert probes.probe_count == 1
    assert probes[-10] == -7 and probes[0] == -7
    assert probes.probe_count == 2


def test_an_out_of_range_index_raises_and_counts_nothing() -> None:
    probes = fresh()
    with pytest.raises(IndexError):
        probes[10]
    with pytest.raises(IndexError):
        probes[-11]
    assert probes.probe_count == 0


def test_a_slice_counts_every_position_it_copies_and_returns_a_plain_list() -> None:
    probes = fresh()
    part = probes[2:6]
    assert part == [0, 2, 5, 8]
    assert type(part) is list
    assert probes.probe_count == 4
    assert probes[::-3] == [55, 13, 2, -7]
    assert probes.probe_count == 4 + 3  # Positions 9, 6, 3 and 0; 3 and 0 are new.


def test_an_empty_slice_counts_nothing() -> None:
    probes = fresh()
    assert probes[5:5] == []
    assert probes.probe_count == 0


def test_iteration_counts_only_what_was_consumed() -> None:
    probes = fresh()
    iterator = iter(probes)
    assert next(iterator) == -7
    assert next(iterator) == -3
    assert probes.probe_count == 2
    assert sum(1 for _ in iterator) == 8
    assert probes.probe_count == 10


def test_reversed_counts_from_the_end() -> None:
    probes = fresh()
    iterator = reversed(probes)
    assert next(iterator) == 55
    assert probes.probe_count == 1
    assert list(iterator) == ITEMS[-2::-1]
    assert probes.probe_count == 10


def test_membership_stops_at_a_hit_and_scans_everything_on_a_miss() -> None:
    probes = fresh()
    assert (2 in probes) is True
    assert probes.probe_count == 4  # Positions 0 to 3.
    other = fresh()
    assert (1 in other) is False
    assert other.probe_count == 10


def test_index_stops_at_a_hit_and_raises_on_a_miss_after_scanning() -> None:
    probes = fresh()
    assert probes.index(8) == 5
    assert probes.probe_count == 6
    other = fresh()
    with pytest.raises(ValueError):
        other.index(100)
    assert other.probe_count == 10
    bounded = fresh()
    assert bounded.index(34, 3, 9) == 8
    assert bounded.probe_count == 6  # Positions 3 to 8.


def test_count_reads_everything() -> None:
    probes = fresh()
    assert probes.count(5) == 1
    assert probes.probe_count == 10


@pytest.mark.parametrize(
    "operation",
    [
        lambda p: p.copy(),
        lambda p: p + [1],
        lambda p: [1] + p,
        lambda p: p * 2,
        lambda p: 2 * p,
        lambda p: p == ITEMS,
        lambda p: p != ITEMS,
        lambda p: p < ITEMS,
        lambda p: p <= ITEMS,
        lambda p: p > ITEMS,
        lambda p: p >= ITEMS,
        lambda p: sum(p),
        lambda p: max(p),
        lambda p: min(p),
        lambda p: sorted(p),
        lambda p: list(p),
        lambda p: tuple(p),
        lambda p: set(p),
        lambda p: [*p],
        lambda p: dict.fromkeys(p),
        lambda p: list(enumerate(p)),
        lambda p: list(zip(p, p, strict=True)),
        lambda p: p.sort(),
        lambda p: repr(p),
    ],
)
def test_whole_list_operations_count_every_position(operation: object) -> None:
    probes = fresh()
    assert callable(operation)
    operation(probes)
    assert probes.probe_count == 10


def test_the_results_of_whole_list_operations_are_correct() -> None:
    probes = fresh()
    assert probes.copy() == ITEMS and type(probes.copy()) is list
    assert probes + [1] == ITEMS + [1] and type(probes + [1]) is list
    assert probes * 2 == ITEMS * 2
    assert sorted(probes, reverse=True) == sorted(ITEMS, reverse=True)
    assert repr(probes) == repr(ITEMS)
    assert probes < [100] and not probes > [100]


def test_a_logarithmic_search_with_the_standard_library_stays_small() -> None:
    probes = ProbeList(list(range(0, 20_000, 2)))  # 10,000 entries.
    spot = bisect.bisect_left(probes, 7_777)
    assert spot == 3889
    assert probes.probe_count <= 14


def test_a_hand_written_binary_search_stays_small_even_reading_twice_per_step() -> None:
    probes = ProbeList(list(range(0, 20_000, 2)))
    target = 12_346
    low, high = 0, len(probes) - 1
    found = -1
    while low <= high:
        mid = (low + high) // 2
        if probes[mid] > target:
            high = mid - 1
        elif probes[mid] < target:
            low = mid + 1
        else:
            found = mid
            break
    assert found == 6173
    assert probes.probe_count <= 14


def test_a_linear_scan_counts_the_whole_list() -> None:
    probes = ProbeList(list(range(10_000)))
    for position in range(len(probes)):
        if probes[position] == -1:
            break
    assert probes.probe_count == 10_000


def test_a_recursive_search_that_slices_copies_too_much() -> None:
    probes = ProbeList(list(range(10_000)))

    def search(numbers: list[int], target: int) -> bool:
        if not numbers:
            return False
        mid = len(numbers) // 2
        if numbers[mid] == target:
            return True
        if numbers[mid] < target:
            return search(numbers[mid + 1 :], target)
        return search(numbers[:mid], target)

    assert search(probes, -5) is False
    assert probes.probe_count > 1_000


def test_two_lists_do_not_share_their_counts() -> None:
    first, second = fresh(), fresh()
    first[0]
    assert second.probe_count == 0
