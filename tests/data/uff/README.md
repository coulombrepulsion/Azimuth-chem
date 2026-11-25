# Эталоны UFF (0.106.0)

`structures.json` — 20 структур Азимута (связи с порядками Кекуле, координаты сдвинуты от минимума). Скрипт
`tools/uff_reference.py`, запущенный Python с RDKit, отдаёт их RDKit и пишет сюда `rdkit_uff.json`: энергию UFF в тех же
координатах, r0 и k каждой связи и энергию после минимизации RDKit. Его читает
`tests/compass/test_uff.py::test_energies_as_rdkit`.

```
<python с RDKit> tools/uff_reference.py
```
