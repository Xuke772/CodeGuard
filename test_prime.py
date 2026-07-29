import pytest
from prime import is_prime

def test_negative():
    assert not is_prime(-1)
    assert not is_prime(-5)

def test_zero_one():
    assert not is_prime(0)
    assert not is_prime(1)

def test_small_primes():
    assert is_prime(2)
    assert is_prime(3)
    assert is_prime(5)
    assert is_prime(7)
    assert is_prime(11)
    assert is_prime(13)
    assert is_prime(17)
    assert is_prime(19)
    assert is_prime(23)
    assert is_prime(29)

def test_small_non_primes():
    assert not is_prime(4)
    assert not is_prime(6)
    assert not is_prime(8)
    assert not is_prime(9)
    assert not is_prime(10)
    assert not is_prime(12)
    assert not is_prime(14)
    assert not is_prime(15)
    assert not is_prime(16)
    assert not is_prime(18)
    assert not is_prime(20)
    assert not is_prime(21)
    assert not is_prime(22)
    assert not is_prime(24)
    assert not is_prime(25)
    assert not is_prime(26)
    assert not is_prime(27)
    assert not is_prime(28)

def test_larger_primes():
    assert is_prime(97)
    assert is_prime(101)
    assert is_prime(103)
    assert is_prime(107)
    assert is_prime(109)
    assert is_prime(113)
    assert is_prime(127)
    assert is_prime(131)
    assert is_prime(137)
    assert is_prime(139)
    assert is_prime(149)
    assert is_prime(151)
    assert is_prime(157)
    assert is_prime(163)
    assert is_prime(167)
    assert is_prime(173)
    assert is_prime(179)
    assert is_prime(181)
    assert is_prime(191)
    assert is_prime(193)
    assert is_prime(197)
    assert is_prime(199)

def test_larger_non_primes():
    assert not is_prime(100)
    assert not is_prime(102)
    assert not is_prime(104)
    assert not is_prime(105)
    assert not is_prime(106)
    assert not is_prime(108)
    assert not is_prime(110)
    assert not is_prime(111)
    assert not is_prime(112)
    assert not is_prime(114)
    assert not is_prime(115)
    assert not is_prime(116)
    assert not is_prime(117)
    assert not is_prime(118)
    assert not is_prime(119)
    assert not is_prime(120)
    assert not is_prime(121)
    assert not is_prime(122)
    assert not is_prime(123)
    assert not is_prime(124)
    assert not is_prime(125)
    assert not is_prime(126)
    assert not is_prime(128)
    assert not is_prime(129)
    assert not is_prime(130)

def test_perfect_squares():
    assert not is_prime(4)
    assert not is_prime(9)
    assert not is_prime(25)
    assert not is_prime(49)
    assert not is_prime(121)
    assert not is_prime(169)

def test_even_numbers():
    for n in range(4, 100, 2):
        assert not is_prime(n)

def test_type_error():
    with pytest.raises(TypeError):
        is_prime("hello")
    with pytest.raises(TypeError):
        is_prime(3.14)
    with pytest.raises(TypeError):
        is_prime([1, 2, 3])
