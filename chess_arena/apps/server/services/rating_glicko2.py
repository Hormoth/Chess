from glicko2 import Player as GPlayer

def update_after_game(white, black, result: str):
    w = GPlayer(rating=white.rating, rd=white.rd, vol=white.vol)
    b = GPlayer(rating=black.rating, rd=black.rd, vol=black.vol)

    if result == "1-0":
        w.update_player([b.rating], [b.rd], [1])
        b.update_player([w.rating], [w.rd], [0])
        white.wins += 1; black.losses += 1
    elif result == "0-1":
        w.update_player([b.rating], [b.rd], [0])
        b.update_player([w.rating], [w.rd], [1])
        white.losses += 1; black.wins += 1
    else:
        w.update_player([b.rating], [b.rd], [0.5])
        b.update_player([w.rating], [w.rd], [0.5])
        white.draws += 1; black.draws += 1

    white.rating, white.rd, white.vol = w.rating, w.rd, w.vol
    black.rating, black.rd, black.vol = b.rating, b.rd, b.vol
