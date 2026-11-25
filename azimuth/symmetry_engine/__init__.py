"""The symmetry engine of Compass and Spectrum (taken out of the Atlas, so the program does not need it).

§1 PURPOSE
    The point group of a molecule, its symmetrised structure (Compass: «Симметрия»), the mean atomic masses (Spectrum:
    thermochemistry). It was read from the Atlas (modules/atlas/atlas_v2/quas_atlas/core, through modules.atlas.paths
    and sys.path); the Atlas leaves the program for the site, the engine stays.
§2 RULES
    The files are the Atlas's own, unchanged (symfind, symmetry with data/symmetry_ct.json, jsmath, libm_glibc —
    LGPL, see its header — and _sincostab): the program and the page «Симметрия» of the Atlas on the site give the
    same group and the same symmetrised coordinates. tests/core/test_symmetry_engine.py checks that the copies are
    the same as the Atlas's while the Atlas is in the repository (a change is made in both, or in neither).
§3 INTERFACE
    from azimuth.symmetry_engine import symfind — classify, analyze, _w (the mean atomic mass), GROUP_GENS, …"""
