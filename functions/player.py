def last_player(player_number: int):
    """
    上家號碼
    Input: 玩家編號(int)
    Output: 上家編號(int)
    """
    last_player = player_number - 1
    if last_player == -1:
        last_player = 3
    return last_player


def next_player(player_number: int):
    """
    下家號碼
    Input: 玩家編號(int)
    Output: 下家編號(int)
    """
    next_player = player_number + 1
    if next_player == 4:
        next_player = 0
    return next_player


def player_number(player_number: int):
    """
    玩家編號
    Input: 玩家編號(int)
    Output: 玩家編號(int)
    """
    if player_number == 0:
        return 4
    else:
        return player_number
