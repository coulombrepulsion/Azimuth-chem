"""Where the labels of the critical points go on the model (drawn by viewer.MoleculeView.draw_aim)."""
def aim_label_places(spots, sizes):
    """The upper left corner of the label of every critical point — (x, y, kind) on the screen, the size (w, h)
    of its label or None — so that it covers no other label and no other point: the first free of eight places
    around the point, the upper right first; the upper right when none is free. A nucleus label keeps clear of its
    atom (a larger gap); the nuclei are rings around the atoms, not dots, so they do not block labels."""
    def hit(a, b):
        return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]

    dots = [(x - 5.0, y - 5.0, 10.0, 10.0) for x, y, kind in spots if kind != 'nucleus']
    placed, out = [], []
    for (x, y, kind), size in zip(spots, sizes):
        if size is None:
            out.append(None)
            continue
        w, h = size
        gap = 11.0 if kind == 'nucleus' else 6.0
        offsets = [(gap, -gap - h), (-gap - w, -gap - h), (gap, gap), (-gap - w, gap), (gap + 2, -h / 2),
                   (-gap - w - 2, -h / 2), (-w / 2, -gap - h - 2), (-w / 2, gap + 2)]
        own = (x - 5.0, y - 5.0, 10.0, 10.0)
        others = [d for d in dots if d != own] + placed
        chosen = next(((x + dx, y + dy) for dx, dy in offsets if not any(hit((x + dx, y + dy, w, h), r) for r in others)),
                      (x + offsets[0][0], y + offsets[0][1]))
        placed.append((chosen[0] - 1.0, chosen[1] - 1.0, w + 2.0, h + 2.0))
        out.append(chosen)
    return out
