def is_prime(n: int) -> bool:
    """判断一个数是否为质数。

    Args:
        n: 要判断的整数

    Returns:
        如果是质数返回 True，否则返回 False
    """
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    
    # 检查从 5 到 sqrt(n) 的数
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    
    return True
