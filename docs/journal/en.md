# What’s new — Quail’s notes

## 0.228.0 — 26 November 2026

- ### 0.228.0 — A draft reaction path in seconds

A reaction path in ORCA can now be found with the fast GFN2-xTB method: choose it in the list of methods, no basis set is needed. In seconds it gives a starting guess of the transition state, to be refined with a DFT functional. The program xtb must be installed.

## 0.227.0 — 26 November 2026

- ### 0.227.0 — The hindered rotor

A soft rotation of a group about a bond is poorly described by a harmonic vibration. Spectrum has a new tool, «Hindered rotor»: give it a scan of the dihedral angle, and it computes by how much the free energy and the equilibrium or rate constant should be corrected.

## 0.226.0 — 26 November 2026

- ### 0.226.0 — The complete basis set and the equilibrium of two forms

For an accurate energy in ORCA you can now choose an extrapolation to the complete basis set: it is a group of its own in the list of basis sets and works with MP2, CCSD(T) and DLPNO-CCSD(T). And Spectrum has a new tool, «Equilibrium of two forms»: give it two results with frequencies and get the equilibrium constant and the shares of the forms from 200 to 600 K, with the contributions of the energy, rotation, vibrations and symmetry.

## 0.225.0 — 26 November 2026

- ### 0.225.0 — The program tells you about a new version

At the start Azimuth now looks whether a newer version is out and offers to download it. You can put it off, skip one version, or switch the check off in the settings. To check yourself: «Help → Check for updates…».

## 0.224.0 — 26 November 2026

- ### 0.224.0 — Reaction rate from the diagram

In the reaction diagram, with ΔG chosen, every barrier now shows the Eyring rate constant of the forward and the reverse reaction, and a unimolecular step its half-life too. The «Copy k(T)» button gives a table of the constants from 200 to 600 K, ready to paste into a report.

## 0.223.0 — 26 November 2026

- ### 0.223.0 — The path from a transition state

Sextant has a new task for ORCA, «Path from the transition state (IRC)». Find a transition state, check that it has one imaginary frequency, and run this task at the same geometry with the same method: ORCA goes down from it both ways. Compass shows which two minima this transition state connects and the energy profile along the path.

## 0.222.50 — 26 November 2026

- ### 0.222.50 — The manual in three languages

The manual book is now in English and in Chinese too — with the same chapters, pictures and tables as the Russian one. The names of buttons and menu items in it are those of the program in that language.

## 0.222.49 — 26 November 2026

- ### 0.222.49 — Calculation programs on Windows

«Install calculation programs» no longer trips over a mirror set in the conda of the computer: xtb and MOPAC come straight from conda-forge. And if an installation still fails, its reason is now in the log instead of a black window that closes at once.

## 0.222.48 — 25 November 2026

- ### 0.222.48 — The manual as a book

The manual is now a real book: one PDF with contents, chapters, pictures of the windows and tables — from installation to the analysis of the electron density. «Help → Manual» opens it; it can be printed or handed out to students. (Russian for now.)

## 0.222.47 — 25 November 2026

- ### 0.222.47 — The password on Windows

On Windows the server window now has a «Remember in Windows» box: the password is kept in the system store and is not asked again after a restart — as in the Keychain on a Mac.

## 0.222.46 — 25 November 2026

- ### 0.222.46 — An open license

Azimuth may now be used freely in teaching, study and non-commercial research — just cite the program; how is written in the README. The tests also no longer look into the Keychain of the computer.

## 0.222.45 — 25 November 2026

- ### 0.222.45 — Its own font, and Windows

The program now brings its own font, Inter, and looks the same on any computer without searching for or downloading anything. I checked it on Windows: fixed small things in the Sextant windows and made sure an ORCA calculation runs there to the end.

## 0.222.44 — 24 November 2026

- ### 0.222.44 — Atlas: EPR and NICS

Two new panels on the Atlas NMR page. One shows why EPR hyperfine constants need a special basis: Gaussian functions miss density at the nucleus. The other shows how a ring current makes NICS negative for aromatic rings and positive for antiaromatic ones.

## 0.222.43 — 24 November 2026

- ### 0.222.43 — Atlas: the error of a calculation

A new Atlas topic, «The error of a calculation: from the error of a method to a conclusion». Add up the errors of the method, the basis and the convergence and see which one decides; go from the mean error of a functional to an interval for your barrier; compute the enthalpy of formation of ethanol through an isodesmic reaction; judge how reliable conformer shares are.

## 0.222.42 — 24 November 2026

- ### 0.222.42 — Atlas: the bond through orbitals

A new Atlas topic, «The bond through orbitals: localization, NBO, NCI». Rotate a pair of orbitals and see that the density does not change while the orbitals settle on the bonds; find the hybridization from the bond angle; compare the donor–acceptor energy E(2) with the exact answer; build the NCI plot for one molecule, a dimer and a ring.

## 0.222.41 — 24 November 2026

- ### 0.222.41 — Atlas: spin states of complexes in DFT

A new Atlas topic, «Spin states of complexes in DFT». Move the share of exact exchange and watch the energy difference of the high and the low spin of three iron(II) complexes change and where it changes sign; check a solution by ⟨S²⟩ and estimate the admixture of another spin state; compare the bond lengths in the two spin states.

## 0.222.40 — 24 November 2026

- ### 0.222.40 — Atlas: conical intersections and biradicals

A new Atlas topic, «Conical intersections and biradicals». See why the curves of one symmetry of a diatomic do not cross while a polyatomic has a whole seam with a double cone; why TD-DFT goes wrong near an S₁/S₀ intersection; how the two-centre model explains the singlet–triplet splitting of the benzynes and how the Yamaguchi formula corrects a broken-symmetry DFT solution.

## 0.222.39 — 24 November 2026

- ### 0.222.39 — Atlas: properties as derivatives of the energy

A new Atlas topic, «Properties as derivatives of the energy». Choose the step of a finite difference and see the error of the formula give way to the rounding noise; compute the dipole moment and the polarizability by the finite-field method and see why it needs a tight SCF convergence; compare the polarizability of water in several basis sets and see it almost halved without diffuse functions.

## 0.222.38 — 24 November 2026

- ### 0.222.38 — Atlas: searching for a transition state

A new Atlas topic, «Searching for a transition state and the reaction path». On model surfaces, walk to a saddle by eigenvector following and see the Newton method roll down into a minimum from the same point; optimize an elastic band with and without the projections of the forces and watch the climbing image find the saddle; see a relaxed scan forward and backward give different profiles.

## 0.222.37 — 24 November 2026

- ### 0.222.37 — Atlas: molecular dynamics and machine learning

Two new topics in a new Atlas section, «Dynamics and machine learning». In the first, choose the integration step and watch the Euler method «heat up» a molecule; see five learned models agree where they were trained and diverge where they were not; estimate whether a trajectory will see a reaction. In the second: why a correction to a cheap method is easier to learn than the energy itself, how many test molecules it takes to tell two models apart, and how stable compounds are picked by the convex hull.

## 0.222.36 — 24 November 2026

- ### 0.222.36 — Atlas: defects, surfaces, adsorption and magnetism

Two new Atlas topics. «Defects and surfaces of crystals»: how many vacancies silicon has at melting and at room temperature, how the charge of a defect depends on the Fermi level, why the surface energy «drifts» when the bulk energy comes from another calculation. «Adsorption and magnetism»: why hydrogen holds on nickel and platinum and not on gold, when a metal becomes a ferromagnet, and why oxides of transition metals need the DFT+U correction.

## 0.222.33 — 24 November 2026

- ### 0.222.33 — Atlas: the properties of crystals

A new Atlas topic, «Properties of crystals: compression, phonons, heat capacity». Fit the equation of state to a series of «calculations» and see how a narrow range of volumes and noise spoil the bulk modulus; watch the difference of the masses open a gap between the acoustic and the optical phonons; compare the heat capacity by Debye and by Einstein for diamond and copper. It helps with projects on elasticity and phonons in Quantum ESPRESSO.

## 0.222.31 — 24 November 2026

- ### 0.222.31 — Two new Atlas topics: crystals from the inside

The Atlas on the site has two new topics: «The Bloch theorem and k-points» and «Band structure and density of states». Move the wave vector and see why k is taken only in the first zone; compare how the energy converges with the k-mesh in a metal and in an insulator; count the plane waves an E<sub>cut</sub> gives; build the bands of a chain and of graphene and see when a gap opens. All of it helps with projects in Quantum ESPRESSO.

## 0.222.27 — 24 November 2026

- ### 0.222.27 — The essentials first

The window that installs calculation programs now ticks only xtb and MOPAC by itself — a good place to start. The large packages say how much they download and how much disk they take, so nothing extra gets installed. And the package manager micromamba is downloaded in a checked version: if the file is not the expected one, the installation does not start.

## 0.222.26 — 23 November 2026

- ### 0.222.26 — An honest refusal of MOPAC

Asked for the frequencies of a molecule that has not been optimized, MOPAC quietly computes nothing — and the program showed such a calculation as a success. Now it says what happened and advises to choose «Optimization + frequencies».

## 0.222.25 — 23 November 2026

- ### 0.222.25 — Caffeine from SMILES and phonons from the server

Molecules with a substituted nitrogen in an aromatic ring — caffeine, N-methylpyrrole — are now built from SMILES correctly: they used to get one hydrogen too many, and the calculation would not start. And after a phonon calculation of Quantum ESPRESSO on the server the modes and the dispersion come back to the computer.

## 0.222.24 — 23 November 2026

- ### 0.222.24 — Quantum ESPRESSO on the server

Calculations of Quantum ESPRESSO on the server now really run in parallel: with some builds the program was started as several separate copies instead of one parallel run.

## 0.222.23 — 23 November 2026

- ### 0.222.23 — CP2K on the server

A calculation of CP2K on the server of the laboratory is now started the way its build needs and runs to the end; before, the program stopped at the start.

## 0.222.22 — 23 November 2026

- ### 0.222.22 — The server window does not jump

When the settings open in the window «Server for calculations», the window no longer changes its height and the fields do not move; the titles of the two cards stand level.

## 0.222.21 — 23 November 2026

- ### 0.222.21 — Three servers checked with calculations

Calculations have run on all three servers of the laboratory, the one without a queue included. Fixed on the way: the program chooses the environment lines for ORCA more exactly, shows what a failed job on the server said itself, and a long answer of the server no longer squeezes the fields of the login window.

## 0.222.20 — 23 November 2026

- ### 0.222.20 — The VPN connects out of sight

When the program asks OpenVPN Connect to connect the VPN, its window no longer jumps over your work: the application gets the command in the background. The window opens only when the VPN has not connected in 15 seconds — it may be waiting for a password then.

## 0.222.19 — 22 November 2026

- ### 0.222.19 — A server without a queue, the 80 % rule and a calm server window

Calculations can now run on a server without SLURM too: a calculation starts there at once and only when the cores are free — with it, no more than 80 % of the cores may be busy. «Get resources» finds the programs outside PATH as well (conda, /opt, the home folder) and writes the environment line they need. The server window no longer stops while the VPN connects, its settings are narrower, and the extra lines are gone.

## 0.222.18 — 22 November 2026

- ### 0.222.18 — Small things in the server window and in Sextant

The button «Server settings» opens the settings at last — it did nothing before. The window of the login to the server is narrower still. And in Sextant the card of the molecule no longer stretches on a large screen: the empty room under the line of the method and the task went to the input file.

## 0.222.17 — 22 November 2026

- ### 0.222.17 — The VPN with one button, and its window out of the way

The window «Server for calculations» now has the buttons «Connect the VPN» and «Disconnect the VPN» next to the list of VPN profiles. And the window of OpenVPN Connect no longer jumps over the program: on a Mac it is hidden at once. If the VPN has not connected in 15 seconds, its window opens by itself — it may be asking for a password.

## 0.222.16 — 22 November 2026

- ### 0.222.16 — Each program on the server has its own environment lines

In the settings of the server the environment lines are now set separately for ORCA, MOPAC, Quantum ESPRESSO and CP2K — the list «Environment lines for» above the field. The lines of one program no longer reach the jobs of another: what CP2K needs does not get in the way of ORCA. The common lines for all jobs stay. And the window of the login to the server is much narrower: the buttons that check the connection and set up the login without a password moved into the card «Login».

## 0.222.15 — 22 November 2026

- ### 0.222.15 — The assistant can compute on the server

The AI assistant that drives Azimuth without its window can now send calculations of ORCA and MOPAC to the SLURM server of your profile. The server is shared, so the rules are strict: the login is by the key only, without a password; cores and memory — no more than are free and no more than half of the node; every calculation has a time limit; at most three calculations at once; everything sent is written into a journal.

## 0.222.14 — 22 November 2026

- ### 0.222.14 — Energies from different programs come with a warning

When a reaction diagram or a set of conformers holds calculations of different programs, Spectrum now says so. It matters: «B3LYP» in ORCA and «B3LYP» in Psi4 or NWChem are different functionals, and the energy of water differs between them by 23 kcal/mol. Also, MOPAC no longer passes off as done a calculation it refused because of overlapping atoms, and the manual has «How to install ORCA» step by step.

## 0.222.13 — 22 November 2026

- ### 0.222.13 — Every task, with a real calculation

Every task in the list of Sextant for ORCA, Psi4, NWChem, xtb and MOPAC was run by the real programs and read back. Several things were found and fixed on the way. A search of a transition state in Psi4 showed the starting geometry instead of the one found. NMR from NWChem was computed but not read. MP2 in NWChem now gives the same energy as in ORCA and Psi4. When a calculation of NWChem does not converge or runs out of memory, the program now says what happened and offers a fix. And after a failure of ORCA there is no longer the extra advice «repeat on one process».

## 0.222.12 — 22 November 2026

- ### 0.222.12 — B3LYP with dispersion from the start

A new window of Sextant now starts with B3LYP-D3(BJ)/def2-SVP: the dispersion correction is on from the beginning. Without it B3LYP barely feels weak attractions — stacked rings, conformers, complexes. For methods D3 is not added to (HF, MP2, ωB97X-D) it switches itself off.

## 0.222.11 — 22 November 2026

- ### 0.222.11 — Thirty molecules of the course, down to a minimum

Thirty molecules of the course — from water to naphthalene — were built from SMILES and computed with «Optimization + frequencies» in xtb and MOPAC without a single edit. Almost all reached a minimum at once; in three a methyl turned the wrong way, and the advice «Shift along the imaginary mode» fixes it in one step. And a very small imaginary frequency, like −11 cm⁻¹ of the methyl of toluene, no longer scares with the words «not a minimum»: it is a nearly free rotation or noise, and the program says so.

## 0.222.10 — 22 November 2026

- ### 0.222.10 — What is not checked yet now shows

What the program can do but what has not yet been checked by real calculations or against other programs is marked «not checked»: Gaussian and GAMESS in the list of programs of Sextant, the calculations and the analysis of crystals, UFF for metals. The tip says why. Checked for the beta: ORCA, xtb, CREST, MOPAC, NWChem and Psi4.

## 0.222.9 — 22 November 2026

- ### 0.222 — A setup without scrolling, Psi4 in one click, molecules from SMILES without saddles

«Calculation setup» no longer scrolls: the card holds what is set most often, the rest is in «Additional settings», and the button «Fields…» decides what stays in view (for a molecule and a crystal). Psi4 is installed by «Install calculation programs» and checked by real calculations: optimization with frequencies, TD-DFT, CCSD(T). A molecule from SMILES no longer lands in a saddle: the methyl of acetaldehyde is right, H₂O₂ is not flat, spiropentane is D2d, and «/» and «\» set cis and trans. The window «Server for calculations» is now the login, and the server settings slide out to the right.

## 0.221.0 — 21 November 2026

- ### 0.221.0 — The «gold standard» — CCSD(T)

The list of methods now has coupled clusters: CCSD(T) in ORCA, Gaussian and Psi4, and its fast local version DLPNO-CCSD(T) in ORCA. It is the most accurate method of the program — the one functionals are compared with. It computes the energy only: optimize the geometry with DFT first, then compute the CCSD(T) energy on it. For water DLPNO differs from the full CCSD(T) by only 0.1 kcal/mol.

## 0.220.0 — 21 November 2026

- ### 0.220.0 — Phonon branches of a crystal

Quantum ESPRESSO now draws the phonon branches along a path through the Brillouin zone and the phonon density of states — like the band structure, but for the vibrations of the lattice. One sees the acoustic branches rise from zero and, in ionic crystals, the longitudinal and transverse optical modes part at Γ. Rock salt gave 165 and 255 cm⁻¹ against 164 and 264 measured; the branches of silicon agree with experiment within a few per cent.

## 0.219.0 — 21 November 2026

- ### 0.219.0 — Crystal vibrations in Quantum ESPRESSO

The vibrational frequencies of a crystal at Γ are now computed by Quantum ESPRESSO too, not only by CP2K. Sextant sets three steps itself: the electrons, the response of the lattice (ph.x) and the analysis of the modes (dynmat.x). For insulators there are also IR intensities and the high-frequency dielectric constant. The modes can be watched on the model of the crystal, as for CP2K before. Silicon gave 514 cm⁻¹ against 520 measured, rock salt 165 against 164.

## 0.218.0 — 21 November 2026

- ### 0.218.0 — The handbook

Help now has a Handbook — what one looks up while preparing a calculation or reading its result. Conversion of units of energy, length and dipole moment and the fundamental constants; solvents — their dielectric constant and the name each program knows them by (the «?» at the solvent in Sextant); the NIST frequency scaling factors by method and basis set — from Spectrum the chosen factor goes straight into the IR spectrum; and where to find measured spectra, geometries and thermochemistry to compare a calculation with — with a search by the formula of the molecule.

## 0.217.2 — 21 November 2026

- ### 0.217.2 — «Task setup» fits again

The fields of Sextant's «Task setup» are no longer cut on the right. The long name of a chain task widened the «Task» list, and the card grew wider than its column. Now the lists follow the column (an open list still shows the names in full), and the column widens only when the fields really need the room. The window that installs programs also names the real folders now: NWChem, Quantum ESPRESSO and CP2K each go to a folder of their own.

## 0.217.1 — 21 November 2026

- ### 0.217.1 — The energy during a TD-DFT spectrum

While ORCA computes an absorption spectrum (TD-DFT), the calculation window shows the energy of the molecule itself. Before, it showed the energy of its first excited state: ORCA prints that one last, and Sextant took it for the result. Azimuth also answers a language model more precisely now: which methods, basis sets and solvents each program accepts, the conformers of CREST, the thermochemistry of MOPAC and the NMR shieldings.

## 0.217.0 — 21 November 2026

- ### 0.217.0 — Azimuth can be driven by a language model

Azimuth now has commands without its window and an MCP server — the standard way to give a language model tools. Connected to the Claude app or to a local model, it can be asked to build a molecule, show the input file, start a calculation, follow it and read the result — with the energy, frequencies, thermochemistry and the doctor's advice if something went wrong. The checks of the program itself are started the same way. How to connect — in the manual and in docs/features/HEADLESS.md.

## 0.216.158 — 21 November 2026

- ### 0.216.158 — NWChem installs from the program

The window «Calculation → Install programs for calculation…» now offers NWChem, a free quantum chemistry program. It goes into a folder of its own inside the program folder, with its own MPI, and is checked at once by a short calculation. On Windows NWChem is not installed this way: there is no ready build for it.

## 0.216.157 — 21 November 2026

- ### 0.216.157 — A more accurate «Convergence» for ORCA

The «Convergence» tab of Spectrum now shows the gradient of an ORCA optimization as ORCA prints it in its «Geometry convergence» table and compares it with the thresholds. Before, another gradient — the Cartesian one — was drawn next to the thresholds, and in the first steps it could be noticeably larger or smaller.

## 0.216.156 — 21 November 2026

- ### 0.216.156 — Each step of a chain with its own method and basis set

Chains of calculations are now in the «Task» list of Sextant itself, after a line. Under the chosen chain its steps are shown: the first is calculated with the settings of the form, and the next ones can have their own method and basis set — for example, optimize in B3LYP/def2-SVP and calculate the UV spectrum in CAM-B3LYP/def2-TZVP. «Run calculation» starts the whole chain.

## 0.216.155 — 21 November 2026

- ### 0.216.155 — Excitation analysis with triplets and a better time estimate

The Multiwfn excitation analysis works again with ORCA TD-DFT where both singlets and triplets are computed: before, it took the wrong state or failed. If the input file was edited by hand, the program asks before starting a queue or a chain whether to start by the settings — the edit does not go into such calculations. The estimate of the calculation time was recalibrated on real calculations and became noticeably more accurate. The fields of «Task setup» in Sextant are no longer cut at the right.


## 0.216.154 — 21 November 2026

- ### 0.216.154 — The fingerprint by the data

The fingerprint of the Hirshfeld surface got a choice of scale. The standard one (0.4–2.6 Å) lets different crystals be compared. The scale «by the data» stretches the axes round the spot itself, which becomes larger and more detailed.


## 0.216.153 — 21 November 2026

- ### 0.216.153 — The axis titles of the fingerprint

The axis titles of the fingerprint of the Hirshfeld surface stand along the axes in bold, as on the other plots of the program.


## 0.216.152 — 21 November 2026

- ### 0.216.152 — Crystal calculations do not take you away from your section

The Hirshfeld surface and the quick xtb of a crystal no longer switch the section by themselves. If you have gone to another section, the quick xtb of a crystal folds into the sign of «Compass · Crystal» in the left panel, as the quick xtb of a molecule does, and a click on the sign brings you back.


## 0.216.151 — 21 November 2026

- ### 0.216.151 — The crystal panels remember what they found

The folded panels Contacts and Hirshfeld surface come back as they were: with the contacts found, the lit button «Show the network», the surface built and its fingerprint. Nothing is computed again.


## 0.216.150 — 21 November 2026

- ### 0.216.150 — The Hirshfeld surface by the button «Build»

The panel of the Hirshfeld surface opens with its settings: the grid, the colouring (d_norm, d_i, d_e, shape index, curvedness) and the molecule. The surface is built by the button «Build». Another colouring of a surface already built appears on the model at once, without computing again.


## 0.216.149 — 21 November 2026

- ### 0.216.149 — The explanations of «?» stay open

A click on «?» now opens a panel with the explanation that does not close by itself: it stays until you click past it, press Esc or click «?» again. Before, the explanation went at the first move of the mouse.


## 0.216.148 — 21 November 2026

- ### 0.216.148 — The network of contacts turns on and off

The button «Show the network» of Contacts is lit blue while the network is on the model, and a second press takes the network away. The side panels of «Compass · Crystal» slide out more evenly, without jerks.


## 0.216.147 — 21 November 2026

- ### 0.216.147 — Quick xtb calculation of a crystal

In «Compass · Crystal» there is now «Calculation → Quick xtb calculation»: the energy, the optimization of the atoms or the optimization together with the cell by GFN1-xTB in CP2K — at once, as the quick xtb of a molecule, without the page of Sextant. The progress is seen over the model, Esc stops it, and the steps of an optimization open in the tab. The Crystal panel now fits its width entirely.


## 0.216.146 — 21 November 2026

- ### 0.216.146 — Crystal calculations only in Sextant

The button «Calculation in Quantum ESPRESSO…» is gone from the Crystal panel and from the toolbar of «Compass · Crystal»: it duplicated Sextant. A crystal calculation is set up in Sextant — with the arrow «To the crystal calculation» at the bottom of «Compass · Crystal».


## 0.216.145 — 21 November 2026

- ### 0.216.145 — Smooth crystal panels

The panels Crystal, Contacts, Hirshfeld surface and Calculation results now slide out and back smoothly, as the panel of the project molecules in «Compass · Molecule».


## 0.216.144 — 21 November 2026

- ### 0.216.144 — Icons in the crystal view menu

The switches of the «Crystal view» menu — symmetry elements, Bravais lattice nodes, displacement ellipsoids, coordination polyhedra, colouring by symmetry and rings — got icons.


## 0.216.143 — 21 November 2026

- ### 0.216.143 — A tidier and faster crystal panel

The buttons of the Crystal panel stand in one row, the sections are set apart by coloured titles, and the fields no longer go past the edge. The panel opens faster: it does not work out the symmetry and the packing again at every press. An error that left the Hirshfeld surface panel empty is fixed. A model with a surface turns more smoothly. The items «Along the x, y, z axis» got icons.


## 0.216.142 — 21 November 2026

- ### 0.216.142 — Clearer reasons for errors, a tidier crystal panel

If a calculation broke with an MPI failure in the middle of an optimization, the program no longer says that «the cycles ran out» — it offers to repeat on fewer processes from the last geometry. When the input file cannot be built, the card now says what exactly is wrong. Texts in the calculation window and in Spectrum no longer run over each other. The Crystal panel is split into sections that unfold, its buttons stay lit while the panel is open and close it with a second press or a click beside it. The Hirshfeld surface is computed without freezing the window.


## 0.216.141 — 21 November 2026

- ### 0.216.141 — The input file is back

After the previous versions the ORCA or Gaussian input file in Sextant sometimes appeared empty and was taken as «edited by hand»: the new syntax highlighting was to blame. This is fixed. The manual and the descriptions of the sections on the home page and in About have been updated — they now include everything added in recent days: the crystal panels, the input file editor, chains of calculations, several calculations on a server, comparing spectra with an experiment and more.


## 0.216.140 — 21 November 2026

- ### 0.216.140 — Several calculations on a server and SLURM settings

On a server the next calculation can now be started without waiting for the previous one to end. The running calculation moves into its own window, and all such windows are listed under «Calculation → Other calculations on the server». The server profile now has the SLURM partition, time limit, project and QoS — needed on large university clusters, where a job without a limit gets little time or is not accepted at all.


## 0.216.139 — 21 November 2026

- ### 0.216.139 — Editor menu and drag and drop of files

The context menu of the input-file editor is split into submenus: find and go to, lines, case, view. The «Files on the server» window got proper colours in the dark theme, a blue «Open in Azimuth» button and drag and drop: files can be dropped into the window from Finder, moved between the panes or dragged out. The selection in the other pane no longer disappears when you switch.


## 0.216.138 — 21 November 2026

- ### 0.216.138 — Doctor, keys and the cluster queue

The doctor of a calculation now offers to continue a stopped optimisation from its last geometry and, if an imaginary frequency remains after an optimisation with frequencies, to shift the molecule along that mode and optimise again. Ctrl+Enter starts a calculation, Ctrl+. stops it. The «Server» menu has «Cluster queue…» — SLURM jobs with the reasons for waiting and the cancel of the chosen ones.


## 0.216.137 — 21 November 2026

- ### 0.216.137 — A chain of calculations

Sextant has a new menu «Calculation → Chain of calculations»: an optimisation with frequencies, then the UV spectrum, the NMR or the energy in a larger basis — with one command. Each next step takes the geometry of the one before, the chain runs as an ordinary queue, and the result of the last step opens in Spectrum.


## 0.216.136 — 21 November 2026

- ### 0.216.136 — Highlighting and «Edit» in Sextant

The input file in Sextant is now coloured: keywords, blocks, the coordinates line, numbers and comments each in their own colour, with rules for each program. The «Edit» menu gained find and replace, go to line, line commands, an input file check and «Insert block» — ready blocks of ORCA (%pal, %maxcore, %scf, %geom, %tddft, SMD solvent, %moinp and others) and Gaussian (%nprocshared, %mem, %chk) that go to their place in the file.


## 0.216.135 — 21 November 2026

- ### 0.216.135 — Projects open from Finder

Projects .qcc now open with a double click in Finder, and Azimuth is offered in «Open With» for files of structures and calculations (.cif, .xyz, .out and others). Silicon joined the crystal examples. README_MACOS.md next to the program says what to do when macOS will not let you open it.


## 0.216.134 — 21 November 2026

- ### 0.216.134 — Search in Help

The Help menu has a search field, as on macOS: type a word and the program lists the menu items and buttons with it and opens the right menu at its place (⌘? opens the search at once). The tasks of Quantum ESPRESSO carry the words of the program — «Cell optimisation (vc-relax)»; after a calculation in the primitive cell the cell of the file is shown too. The items of the crystal view got tooltips, and the model no longer flies away with the trackpad inertia.


## 0.216.133 — 21 November 2026

- ### 0.216.133 — A full editor of the input file and the files on the server

The input file in Sextant is now edited in a full editor: line numbers, find and replace (with regular expressions), go to line, duplicating, moving and commenting lines, case, wrap, zoom — with keyboard shortcuts (F1 lists them all). «Files on the server» gained keys and new features: F3 view, F6 move, Shift+F6 rename, Shift+F4 new file, Alt+F7 find, Ctrl+D favourite folders, Insert and mask marking, sorting, and a function key bar at the bottom.


## 0.216.132 — 21 November 2026

- ### 0.216.132 — Calculation results of a crystal

«Compass · Crystal» has a «Calculation results» panel (the «Calculation» menu and a button on the panel). To the right of the model it lists all calculations of the crystal: energy, pressure, whether it converged; for the chosen one also the band gap, the number of steps, the cell and the folder. The steps, charges, AIM bonds and Spectrum open from there too.


## 0.216.131 — 21 November 2026

- ### 0.216.131 — Crystal menus in groups

The «Crystal» and «Calculation» menus of «Compass · Crystal» are arranged in groups: intermolecular interactions, structure and packing, cell and lattice; charges, AIM bonds and fields on the model. Before, each had seventeen items in a row.


## 0.216.130 — 21 November 2026

- ### 0.216.130 — A panel of its own for the crystal

«Compass · Crystal» now has a button panel of its own: the cell, the view of the crystal, contacts, the Hirshfeld surface, the powder pattern and the calculation in Quantum ESPRESSO, without the buttons for optimising a molecule. Buttons rearranged in the crystal do not change the molecule panel, and the other way round.


## 0.216.129 — 21 November 2026

- ### 0.216.129 — The Crystal panel

The settings of a crystal open in a panel to the right of the model, not in a window over it. There is no «Build» button any more: the model is rebuilt as soon as the number of cells, the range of coordinates or the check boxes change.


## 0.216.128 — 21 November 2026

- ### 0.216.128 — Coordinates of a crystal

The «Coordinates» tab in «Compass · Crystal» shows the independent atoms in fractions of the cell, with the group, the cell and the volume above the table. A row of the table selects all copies of the atom on the model. The CIF of the crystal, POSCAR and the extended XYZ are there too. The inputs for a calculation of a molecule (ORCA, Gaussian and others) are grey for a crystal.


## 0.216.127 — 21 November 2026

- ### 0.216.127 — Contacts beside the model

In «Compass · Crystal», «Contacts» and «Hirshfeld surface» open in a panel to the right of the model instead of separate windows. A row chosen in the table is drawn on the model and its atoms are selected. «Show the network» draws the contacts found as dashed lines, and the Hirshfeld surface goes onto the model at once.


## 0.216.126 — 21 November 2026

- ### 0.216.126 — Crystal examples

In «Compass · Crystal», «Open example…» now offers a menu of crystals: CsCl, NaCl, graphite, benzoic acid. «Another file…» opens the folder of crystal examples, not the common folder of molecules.


## 0.216.125 — 19 November 2026

- ### 0.216.125 — VCD and emission in Spectrum

The vibrations show the VCD spectrum of ORCA and Gaussian; after an optimization of an excited state — the fluorescence or phosphorescence, the Stokes shift and the radiative lifetime.


## 0.216.124 — 19 November 2026

- ### 0.216.124 — Fitted to the experiment at once

A measured spectrum laid over the plot is fitted at once: the frequency factor or the energy shift is set by itself.


## 0.216.123 — 19 November 2026

- ### 0.216.123 — Spectra from NIST

A measured IR or UV-Vis spectrum can be found in the NIST Chemistry WebBook right from Spectrum and laid over the computed one.


## 0.216.122 — 19 November 2026

- ### 0.216.122 — Experiment and conformers in Spectrum

A measured spectrum can be laid over the computed IR, UV-Vis and ECD, with how alike they are and a fitted frequency factor or energy shift; the spectra of conformers are Boltzmann-averaged.


## 0.216.121 — 19 November 2026

- ### 0.216.121 — Compass · Crystal: Z, grey items, menus

For a molecular crystal Z and the formula are now counted by its molecules (C6Cl6, Z = 2), not by the simplest formula. The items of the «Calculation» menu that have no run to show are grey, and the tooltip says what to do. Menus at the right edge no longer go off the screen, and the bottom row is not squeezed. A project with several crystals says which one is shown.


## 0.216.120 — 19 November 2026

- ### 0.216.120 — The «Crystal» window fits the screen

The window of the settings of a crystal no longer goes past the edge of the screen: the settings scroll, and the «Close» and «Build» buttons are always seen at the bottom.


## 0.216.119 — 19 November 2026

- ### 0.216.119 — A project of calculations of any program

«Project from calculations…» now takes the calculations of Gaussian, Psi4, xtb, MOPAC, GAMESS, NWChem and Q-Chem with their files: the Gaussian checkpoint of %chk, the xtb files of fixed names, the NWChem .movecs, Molden and fchk files. The files of orbitals are copied so that Spectrum finds them at once.


## 0.216.118 — 19 November 2026

- ### 0.216.118 — A project of calculations: checked on real calculations

The SCF of a free atom ORCA writes beside an output («…_atom38.out») is no longer taken for a calculation of its own. Different conformers are not joined into one molecule. A copy of an output is taken once. The energy is read also from outputs without «FINAL SINGLE POINT ENERGY» (for example, with Extrapolate).


## 0.216.117 — 19 November 2026

- ### 0.216.117 — One molecule computed in several ways

In a project made of calculations, the same molecule computed by different methods or from different starting geometries now becomes one molecule of the project, each calculation in its history. Conformers stay molecules of their own.


## 0.216.116 — 19 November 2026

- ### 0.216.116 — A project of calculations done elsewhere

«File → Project from calculations…» makes a project of a folder of ORCA or Gaussian calculations. Each output with the files of its name (.gbw, .hess, .xyz…) becomes a calculation of the project with its energy and final geometry. The calculations of one molecule — an optimization, frequencies, TD-DFT — go into one molecule. The files are copied into the project, the originals are not changed. Spectrum, the orbitals and Multiwfn work at once.


## 0.216.115 — 19 November 2026

- ### 0.216.115 — A batch of crystals

A project with several crystals now has a batch mode. Tick the crystals and press «Run calculation» of Quantum ESPRESSO or CP2K: they are computed in turn with the same settings. For an optimization with the cell the pressure can be set — one for all, or each crystal its own, from its CRYSTAL output. A table of energies, pressures and volumes opens at the end.


## 0.216.114 — 19 November 2026

- ### 0.216.114 — The method and energy of a crystal in the project list

The method, basis set and energy of a CRYSTAL output now really reach the list of the project. The «Batch» tab of a crystal project is grey: batch calculations exist for molecules only.


## 0.216.113 — 19 November 2026

- ### 0.216.113 — The basis set of a CRYSTAL output

A CRYSTAL output now shows its basis set. A basis set of the library is found by the BASISSET keyword. For a basis set written by hand, the name is taken from the file name (marked as such) together with the number of atomic orbitals. HF-3c and PBEh-3c are now called by their own names.


## 0.216.112 — 19 November 2026

- ### 0.216.112 — A CRYSTAL output keeps its space group

A CRYSTAL output with a primitive group, such as calcium formate in P C A B (Pbca), now opens in its own group instead of P 1. The list of the project shows the formula, the number of atoms, the method and the energy of its crystals.


## 0.216.111 — 19 November 2026

- ### 0.216.111 — A proton changes the charge by one

«Add proton» and «Remove proton» again change the charge of the molecule by exactly one, not by two.


## 0.216.110 — 19 November 2026

- ### 0.216.110 — Several crystals in one project

A crystal opened while a crystal project is shown is now added to that project instead of opening a new one. The list of the project shows all its crystals: a click on a row shows the crystal with its calculations. To open a crystal in a project of its own, make the project with «+».


## 0.216.109 — 19 November 2026

- ### 0.216.109 — What does not suit a crystal is grey

Oxidation states, the Madelung energy, bond valences and ionic radii are now grey for crystals with organic molecules or ions, and the tooltip says why. The search of conformers is not offered for a crystal either: move a molecule to a molecule tab and search there.


## 0.216.108 — 19 November 2026

- ### 0.216.108 — CRYSTAL outputs from a cluster open

A CRYSTAL output that starts with messages of the queue and a long input with basis sets now opens as a crystal, not with the error «an output of ORCA».


## 0.216.107 — 19 November 2026

- ### 0.216.107 — A narrower element card

The element card of the periodic table is narrower, so the window fits on the screen.


## 0.216.106 — 19 November 2026

- ### 0.216.106 — Colours in the periodic table

The periodic table colours the elements by family, with a legend; an element's card no longer stretches the window.


## 0.216.105 — 19 November 2026

- ### 0.216.105 — A tidier periodic table

The periodic table is framed, with groups, periods and labelled lanthanides and actinides; an element's card opens beside it in a frame of its own and hides on a second click.


## 0.216.104 — 19 November 2026

- ### 0.216.104 — The periodic table

«Help» has the periodic table: a click on an element shows its atom, particles, configuration and isotopes.


## 0.216.103 — 19 November 2026

- ### 0.216.103 — Isotopes by NIST

The masses and abundances of the isotopes are checked against the table of NIST.


## 0.216.102 — 19 November 2026

- ### 0.216.102 — Isotopes in the periodic table

The right button on an element of the periodic table chooses its isotope.


## 0.216.101 — 19 November 2026

- ### 0.216.101 — Isotopes of all the elements

The menu of an atom has every stable isotope of any element and a mass of one’s own.


## 0.216.100 — 19 November 2026

- ### 0.216.100 — An isotope from the menu of an atom

An isotope is chosen with the right button on an atom, the atom is labelled D, ¹³C …; ORCA, Gaussian and Psi4 take isotopes.


## 0.216.99 — 19 November 2026

- ### 0.216.99 — A check before a calculation

Before a calculation is started the program checks the structure itself and asks when it finds errors.


## 0.216.98 — 19 November 2026

- ### 0.216.98 — ChemDraw

Compass opens ChemDraw drawings (.cdxml).


## 0.216.97 — 19 November 2026

- ### 0.216.97 — Isotopes

The selected atoms can get an isotope — D, ¹³C, ¹⁸O …; ORCA calculates the frequencies with their masses.


## 0.216.96 — 19 November 2026

- ### 0.216.96 — «?» in the solvent window

The description of the ways of the solvent is in a question mark; switched-off number fields are grey.


## 0.216.95 — 19 November 2026

- ### 0.216.95 — The solvent window stays

«Remove the solvent» does not close the window — another can be chosen at once.


## 0.216.94 — 19 November 2026

- ### 0.216.94 — The first coordination shell

The solvent stands on the lone pairs — two on an oxygen — as many as fit; the window has «Remove the solvent».


## 0.216.93 — 19 November 2026

- ### 0.216.93 — A more exact first shell

A flat nitrogen is not counted as an acceptor; the message about the places of the first shell is clearer.


## 0.216.92 — 19 November 2026

- ### 0.216.92 — The solvent does not grow in layers

A new solvent goes round the structure itself, even when a solvent is there already.


## 0.216.91 — 19 November 2026

- ### 0.216.91 — Remove the solvent

The molecules of a solvent round the structure go with one command.


## 0.216.90 — 19 November 2026

- ### 0.216.90 — The first shell does not grow as a chain

«Surround with a solvent» again does not build chains from the solvent put before.


## 0.216.89 — 19 November 2026

- ### 0.216.89 — The places of the first shell

When there are more molecules of solvent than places in the first shell, the program says so.


## 0.216.88 — 19 November 2026

- ### 0.216.88 — The first shell of the solvent

The solvent goes to the first shell first — by hydrogen bonds to the polar centres.


## 0.216.87 — 19 November 2026

- ### 0.216.87 — Icons of the new tools

The structure check, the solvent and the protons have icons of their own.


## 0.216.86 — 19 November 2026

- ### 0.216.86 — Structure check, solvent, protons

Compass can check a structure before a calculation, surround it with molecules of a solvent, and add, take off and carry protons.


## 0.216.85 — 19 November 2026

- ### 0.216.85 — A tidier server window

The answer of the server is on a line of its own; the fields of the window no longer overlap.


## 0.216.84 — 19 November 2026

- ### 0.216.84 — Messages seen on «Coordinates»

The message of a copy is seen on the tab «Coordinates» too.


## 0.216.83 — 19 November 2026

- ### 0.216.83 — The light blue behind the notes

In the journal the light blue ground is behind the list of changes, not the head.


## 0.216.82 — 19 November 2026

- ### 0.216.82 — Colons in forms

The name of a row before its field ends with a colon.


## 0.216.81 — 19 November 2026

- ### 0.216.81 — Settings windows with a title

The settings windows of Compass open with their title bar, as the colour picker.


## 0.216.80 — 19 November 2026

- ### 0.216.80 — Semibold headings of groups

The headings of groups with the gold line are semibold.


## 0.216.79 — 19 November 2026

- ### 0.216.79 — The colour picker in frames

The blocks of the colour picker are in frames with headings.


## 0.216.78 — 19 November 2026

- ### 0.216.78 — The groups of styles in frames

In the windows of the styles of the model the groups with headings stand in frames.


## 0.216.77 — 19 November 2026

- ### 0.216.77 — One own set of colours

The custom colours are shared by all settings and kept; «Bond style» has a heading at its top.


## 0.216.76 — 19 November 2026

- ### 0.216.76 — A tidier colour picker

The basic colours by hue, a pipette instead of a button, no «HTML»; opening does not change the height of the window.


## 0.216.75 — 19 November 2026

- ### 0.216.75 — The buttons of the colour picker stay

«OK» and «Cancel» do not move when the palette opens; the window folds back to its size.


## 0.216.74 — 19 November 2026

- ### 0.216.74 — A new colour picker

The sets of colours first; the palette and the numbers open with «Choose by hand».


## 0.216.73 — 19 November 2026

- ### 0.216.73 — The colour picker, tooltips, gold

The colour picker is laid out anew without empty space; the tooltips are shorter; the gold is lighter and shows on «To the calculation settings».


## 0.216.72 — 19 November 2026

- ### 0.216.72 — The headings of groups stand out

The headings of the groups of settings windows are bold and underlined in gold.


## 0.216.71 — 19 November 2026

- ### 0.216.71 — A wider palette, gold on the blue buttons

The field of hues of the colour picker is as wide as its column; the blue buttons get a gold frame under the mouse.


## 0.216.70 — 19 November 2026

- ### 0.216.70 — The colour picker opens again

A fault that kept the colour picker from opening is fixed.


## 0.216.69 — 19 November 2026

- ### 0.216.69 — An even colour picker, a blue OK

The colour picker is laid out evenly; the OK button of every window is blue.


## 0.216.68 — 19 November 2026

- ### 0.216.68 — Rounded menus

All the menus of the right button have rounded corners, as the others.


## 0.216.67 — 19 November 2026

- ### 0.216.67 — A copy says so

After a copy by a button the program says what was copied.


## 0.216.66 — 19 November 2026

- ### 0.216.66 — The menu and the ring of the axes

The items of the axes and of the panel are in one menu; the ring around the axes is centred on them.


## 0.216.65 — 19 November 2026

- ### 0.216.65 — Esc stops a calculation

Esc stops a running calculation again, even right after you clicked the model.


## 0.216.64 — 19 November 2026

- ### 0.216.64 — The question about quitting comes

The question «Quit the program? The calculation will be stopped» now also comes when the window is closed with the button of its title or with ⌘Q.


## 0.216.63 — 19 November 2026

- ### 0.216.63 — Quitting during a calculation

If the program is closed during a calculation, it asks whether to quit: the calculation will be stopped. «Stop and quit» closes the program, «Cancel» lets the calculation go on.


## 0.216.62 — 19 November 2026

- ### 0.216.62 — «A calculation is going on: …»

The message that an action cannot be done now starts with «A calculation is going on:» and then names which one.


## 0.216.61 — 19 November 2026

- ### 0.216.61 — Fixes of the pill of a calculation and of the hint about the properties

The hint about the properties of a result again names the «Atoms», «Bonds», «Dipole and forces» buttons where they stand. Messages during a calculation reliably stand above the pill of the calculation.


## 0.216.60 — 19 November 2026

- ### 0.216.60 — Bader charges are kept

The charges and spins of AIM (the Bader basins) now come back when the result is opened again, like the other charges computed. Those computed before need to be computed once more.


## 0.216.59 — 19 November 2026

- ### 0.216.59 — The pill of a calculation apart from the messages

The line of a calculation going on, with the sign of its section, now has a pill of its own, and the other messages come above it and are no longer overwritten.


## 0.216.58 — 19 November 2026

- ### 0.216.58 — A clear refusal while a calculation runs

If something cannot be done while a calculation runs, the warning now comes on a pill of its own and does not vanish at once. During a calculation «+» makes a new project without opening it, and the tabs of other projects can be opened when the calculation is over.


## 0.216.57 — 19 November 2026

- ### 0.216.57 — The hint knows where your buttons are

The hint about the properties of a result names the «Atoms», «Bonds», «Dipole and forces» buttons where they stand now — above the model or right of it; if they were taken off the panels, it points to the «Calculation» menu.


## 0.216.56 — 19 November 2026

- ### 0.216.56 — The hint about the properties — once, with the right place of the buttons

The hint about the properties of the atoms and bonds in a result now says that the buttons are right of the model, and it comes once for a result, not every time the molecule is chosen.


## 0.216.55 — 19 November 2026

- ### 0.216.55 — «Forces on the atoms» switched on without an error

Switching on «Forces on the atoms» for a result without a gradient of the last geometry no longer gives an error: the steps of the optimization open, and the forces are seen on the last step that has them.


## 0.216.54 — 19 November 2026

- ### 0.216.54 — Forces on the atoms are seen; the eraser says what it removed

If the final geometry has no gradient, «Forces on the atoms» opens the steps of the optimization at the last step with forces and shows them there. The eraser now names what exactly it removed from the model: charges, bond orders, the dipole or the forces.


## 0.216.53 — 19 November 2026

- ### 0.216.53 — The message names the work in progress

If something else is pressed while a calculation runs in a panel (of orbitals or a surface, for example), the message now names the work itself instead of «“Calculating” is in progress».


## 0.216.52 — 19 November 2026

- ### 0.216.52 — A calculation is deleted with its folder

The «Delete the calculation» button in the history of the calculations of a molecule now also deletes the folder of that calculation on the disk (unless another calculation uses it). The program asks before deleting.


## 0.216.51 — 19 November 2026

- ### 0.216.51 — An extra calculation can be removed from the history

In the «History of the calculations of the molecule» window, the chosen calculation can be removed with «Remove from the history» or the Delete key; its files stay in their folder. The number of the attempt is no longer shown twice.


## 0.216.50 — 18 November 2026

- ### 0.216.50 — The axes can be dragged

The axes in the field of Compass are dragged with the mouse and keep their place; they can be put back in the corner.


## 0.216.49 — 18 November 2026

- ### 0.216.49 — A Chinese translation fixed

The message about a calculation shown fills in its number and project in Chinese again.


## 0.216.48 — 18 November 2026

- ### 0.216.48 — A tooltip for cut cells

A long name or method in the list of molecules is shown whole on hover.


## 0.216.47 — 18 November 2026

- ### 0.216.47 — The list of the molecules of a project

The columns of the list of molecules are chosen and resized, it shows the method of the calculation and the history of the calculations of a molecule; a name found becomes the name of the molecule.


## 0.216.46 — 18 November 2026

- ### 0.216.46 — No question about a calculation on a server

At the start the program no longer asks about a calculation on a server: the project opened checks it by itself.


## 0.216.45 — 18 November 2026

- ### 0.216.45 — The project watches its calculations on a server

A project that is opened connects to the server by itself and shows how its calculations started before the exit go on.


## 0.216.44 — 18 November 2026

- ### 0.216.44 — The chosen calculation is current

A calculation of a molecule that is opened becomes its current one; the next calculation done becomes current by itself again.


## 0.216.43 — 18 November 2026

- ### 0.216.43 — All calculations of a molecule

In the “History of the molecule's calculations” any of its calculations opens in Spectrum with “Open result”, and the current result of the molecule stays; xtb calculations are labelled by their own method.


## 0.216.42 — 18 November 2026

- ### 0.216.42 — What was computed is kept

Charges, delocalization, the last map and profile, and the critical points computed from the wavefunction are shown again when you open the same result — without computing again; they are loaded only when their tab is opened, so a large project opens just as fast.


## 0.216.41 — 18 November 2026

- ### 0.216.41 — QTAIM without a second search

The critical points found are kept beside the calculation and shown again when you open the same result — Multiwfn is not run again.


## 0.216.40 — 18 November 2026

- ### 0.216.40 — No false “the geometry changed”

The program no longer says the geometry of a molecule changed when it differs from the result of its optimization by only thousandths of an ångström.


## 0.216.39 — 18 November 2026

- ### 0.216.39 — A result in its project

An output file of a project's calculation now opens with its project and molecule instead of a separate draft; “Continue” no longer offers drafts holding only files looked at.


## 0.216.38 — 18 November 2026

- ### 0.216.38 — The name follows the formula

When a molecule named by its formula is changed, on saving it and its project take the new formula; the names you gave yourself stay.


## 0.216.37 — 18 November 2026

- ### 0.216.37 — Each tab its own view

Each tab now remembers how its molecule is turned and zoomed: turning it in one tab no longer carries over to another.


## 0.216.36 — 18 November 2026

- ### 0.216.36 — Internal order

An internal fix after the checks: the quick xtb calculation works as before.


## 0.216.35 — 18 November 2026

- ### 0.216.35 — The arrow — fixed

The highlight of the “Continue” arrow with the stack open is fixed for good.


## 0.216.34 — 18 November 2026

- ### 0.216.34 — The arrow highlight

The highlight of the “Continue” arrow with the stack open now always follows the pointer itself.


## 0.216.33 — 18 November 2026

- ### 0.216.33 — The arrow follows the pointer

The highlight of the “Continue” arrow now follows the pointer more exactly while the stack opens.


## 0.216.32 — 18 November 2026

- ### 0.216.32 — The right section of a calculation

A calculation started right after another one is now always shown in its own section.


## 0.216.31 — 18 November 2026

- ### 0.216.31 — Cards one after another

The cards of the latest projects slide out from under one another in turn — the second from under the first, the third from under the second — and fold back the same way.


## 0.216.30 — 18 November 2026

- ### 0.216.30 — The arrow stays lit

The “Continue” arrow stays lit when the stack opens under a still pointer.


## 0.216.29 — 18 November 2026

- ### 0.216.29 — Cards from under “Continue”

The cards of the latest projects now slide out from under the “Continue” card and slide back under it.


## 0.216.28 — 18 November 2026

- ### 0.216.28 — A smooth stack

The cards of the latest projects now come out and gather smoothly, without a jerk; the arrow is larger and points up while the stack is open.


## 0.216.27 — 18 November 2026

- ### 0.216.27 — A stack of recent ones

The latest projects on the home page — up to five — come out from under the card as a stack and gather back when the list closes.


## 0.216.26 — 18 November 2026

- ### 0.216.26 — Recent ones as cards

The list of the latest projects on the home page now looks like the “Continue” card itself: the icon, the date and the name.


## 0.216.25 — 18 November 2026

- ### 0.216.25 — Recent projects on the home page

“Continue” on the home page keeps the molecule and the crystal; the down arrow on a card lists the latest projects of that part of Compass.


## 0.216.24 — 18 November 2026

- ### 0.216.24 — Quick xtb without a window

The quick xtb calculation in Compass now runs on the pill over the model with the turning compass, without a separate window; the “Put away” button of the conformer search is the crossed-out eye, as in the calculation window.


## 0.216.23 — 18 November 2026

- ### 0.216.23 — A tick after the calculation

When a calculation ends while you are in another section, its sign stays in the left panel with a gold ring and a tick; a click takes you to the result.


## 0.216.22 — 18 November 2026

- ### 0.216.22 — Steps of a calculation stay together

When a calculation goes in several steps and you go to another section, its sign stays in the left panel until all the steps end.


## 0.216.21 — 18 November 2026

- ### 0.216.21 — A calculation no longer holds the window

During a calculation you can go to other sections and press buttons; a second calculation and a change of tab wait for it to end. In another section the running calculation shows as the sign of its section in the left panel — a click takes you back.


## 0.216.20 — 18 November 2026

- ### 0.216.20 — The calculation sign leads to Sextant

A click on the sign of a running calculation in the left panel now takes you to Sextant and its calculation card instead of opening a separate window.


## 0.216.19 — 18 November 2026

- ### 0.216.19 — Mayer orders without breakage

“Bonds from Mayer orders” no longer breaks the model: the delocalized bonds of a ring are drawn aromatic, and a project saved after this error opens again.


## 0.216.18 — 18 November 2026

- ### 0.216.18 — Hirshfeld again

Hirshfeld charges computed from the wavefunction can now be computed again, like the others; the item stays grey only when the calculation program already printed them.


## 0.216.17 — 18 November 2026

- ### 0.216.17 — Shorter analysis messages

After an analysis the program only says the tables are in the “Analysis” folder of the calculation instead of listing the files; a button opens the folder.


## 0.216.16 — 18 November 2026

- ### 0.216.16 — Waits shown in Spectrum

The delocalization calculation and the critical point search in Spectrum show the pill with the turning ring and the time again.


## 0.216.15 — 18 November 2026

- ### 0.216.15 — More room for the profile

In “Maps and profiles” the profile gets all the room the map buttons leave from the start.


## 0.216.14 — 18 November 2026

- ### 0.216.14 — The map in the middle

The plane map now fills the field in its true proportions and stands in the middle, not pressed to the top edge.


## 0.216.13 — 18 November 2026

- ### 0.216.13 — Weak bonds at once

The weak interactions found now appear on the model right after the critical point search, without waiting for “On the model”.


## 0.216.12 — 18 November 2026

- ### 0.216.12 — No leftovers of the last search

A new critical point search writes its tables over the old ones and now removes the tables it no longer has, so nothing is left from the search before.


## 0.216.11 — 18 November 2026

- ### 0.216.11 — Weak bonds stay

The weak interactions found stay on the model when the critical points are taken off it.


## 0.216.10 — 18 November 2026

- ### 0.216.10 — Weak bonds on the model

Hydrogen, halogen and other weak interactions found by the critical point search are now drawn on the model as lines between the atoms, each kind in its own style.


## 0.216.9 — 18 November 2026

- ### 0.216.9 — Covalent bond

In the table of critical points ordinary bonds between atoms are now called covalent, not chemical.


## 0.216.8 — 18 November 2026

- ### 0.216.8 — A hydrogen bond by its critical point

A weak hydrogen bond with a smaller angle than usual — such as the C–H···O inside caffeine — is now named a hydrogen bond when a bond critical point confirms it.


## 0.216.7 — 18 November 2026

- ### 0.216.7 — A larger vibration

The molecule in the vibration field now fills the field however large it is, instead of staying small in the middle.


## 0.216.6 — 18 November 2026

- ### 0.216.6 — Buttons by the vibration

The vibration field in Spectrum has small buttons in its top right corner to turn and zoom the molecule, and the molecule is shown larger from the start.


## 0.216.5 — 18 November 2026

- ### 0.216.5 — A blue arrow

In the dark theme the “To the calculation settings” button is now the same blue as the language button, not pale blue.


## 0.216.4 — 18 November 2026

- ### 0.216.4 — Critical points are kept

Critical points no longer disappear when you go to Compass · Crystal and back: Compass’s panel and Spectrum’s table show them again, and the orbitals aren’t read from the file again.


## 0.216.3 — 18 November 2026

- ### 0.216.3 — Only the points of that kind

A double click on a critical point in Spectrum shows only the points of the same kind in Compass — only the bond points, say — and the list on Compass’s panel switches to that kind.


## 0.216.2 — 18 November 2026

- ### 0.216.2 — CRYSTAL tables open

A CRYSTAL output with elastic constants and a TOPOND output now open without an error.


## 0.216.1 — 18 November 2026

- ### 0.216.1 — CRYSTAL keywords by the manual

The CRYSTAL input file is checked against the CRYSTAL23 manual: PBE and PBEsol without a hybrid are written as CRYSTAL expects them; the basis sets now include STO-6G and the new pob-rev2.


## 0.216.0 — 18 November 2026

- ### 0.216.0 — CRYSTAL

Azimuth now understands CRYSTAL. For a crystal in Compass you can write a CRYSTAL input file: choose the task (an optimization, also under pressure, elastic constants, frequencies), the functional and the basis set — and save it. A finished CRYSTAL output opens as a crystal: the last structure, the steps of the optimization, the energy, the pressure and the gap, the elastic constants as a table. An output of TOPOND shows a table of the critical points of the density.


## 0.215.10 — 18 November 2026

- ### 0.215.10 — A smaller tick of a calculation

The mark of the end of a calculation on the sign in the left panel (a tick, a cross or a bar) is smaller and moved into the corner.


## 0.215.9 — 18 November 2026

- ### 0.215.9 — Margins in the message pills

The text of the message pills no longer touches their edges: it now has visible margins around it, in long messages too.


## 0.215.8 — 18 November 2026

- ### 0.215.8 — The compass for the quick xtb calculation

While a quick xtb calculation started in Compass runs, the left panel shows the turning compass, not the sextant.


## 0.215.7 — 18 November 2026

- ### 0.215.7 — File windows start in the folder of projects

The «Open…» windows first show the folder of the projects of Azimuth, and if you opened a file from another folder, they start there next time. Saving files elsewhere no longer affects this.


## 0.215.6 — 18 November 2026

- ### 0.215.6 — The molecule does not drift on a repeated search

When conformers are searched again, the molecule no longer shifts to the right, and no shadow passes over the panel of conformers.


## 0.215.5 — 18 November 2026

- ### 0.215.5 — The panel of conformers does not blink

After a conformer search, its panel in Compass opens once and stays open: the model no longer moves away and back.


## 0.215.4 — 18 November 2026

- ### 0.215.4 — No strip of shadow and no empty columns

After a conformer search, no strip of shadow is left at the edge of the model field. The table of conformers shows only the columns with values: the steric score for the candidates of the turns, the energies after xtb.


## 0.215.3 — 18 November 2026

- ### 0.215.3 — The conformer search without extra results

When conformers are searched with «Refine in xtb at once», only the result of xtb is shown, without the intermediate table of the turns. The open panel of conformers no longer jerks when it is updated.


## 0.215.2 — 18 November 2026

- ### 0.215.2 — Dragging several molecules is more reliable

Several molecules are now carried by the program itself: the pile follows the cursor smoothly, and a project tab or «+» gets a frame when the pile is over it. Switching to a project from which the last opened molecule was carried away no longer gives an error.


## 0.215.1 — 18 November 2026

- ### 0.215.1 — A frame round «+»

When molecules are carried over «+», it gets a frame, as a project tab does.


## 0.215.0 — 18 November 2026

- ### 0.215.0 — A new project by dragging onto «+»

Molecules from the project list can be dragged onto the «+» beside the tabs — they make a new project (with ⌥ / Alt they are copied). After the pile lays back, the molecules stay selected.


## 0.214.7 — 18 November 2026

- ### 0.214.7 — The pile gathers without jerks

Molecules gather into the pile before the system begins the drag, so the gathering is smooth and the pile catches up with the cursor.


## 0.214.6 — 18 November 2026

- ### 0.214.6 — A smoother pile that lays out from under the top card

Molecules gather into the pile more smoothly. When it lays out, the top card stays on top and the others come out from under it to their places.


## 0.214.5 — 18 November 2026

- ### 0.214.5 — The pile comes back to the list

If the pile of molecules is released away from the list, it now flies back to the list whole and only there lays out into its rows.


## 0.214.4 — 18 November 2026

- ### 0.214.4 — Dragging molecules no longer hangs

Dragging several molecules no longer hangs the program, and the pile no longer stays on the screen after the release.


## 0.214.3 — 18 November 2026

- ### 0.214.3 — The pile without a delay and solid throughout

After the release, the pile of molecules no longer vanishes: it lays back at once, without a delay. All the cards of the pile and the flying rows are now opaque.


## 0.214.2 — 18 November 2026

- ### 0.214.2 — The pile of molecules is solid and lays back

Molecules dragged together are now opaque: they leave their places in the list for the pile at the cursor, and after the release they lay back — in their new places or the old ones.


## 0.214.1 — 18 November 2026

- ### 0.214.1 — Molecules gather into a pile

When several molecules are dragged from the project list at once, they fly to the cursor and gather into a pile showing their number.


## 0.214.0 — 18 November 2026

- ### 0.214.0 — A molecule can be dragged into another project

Molecules from the project list can be dragged onto the tab of another project: they move there and its tab opens. With ⌥ (Alt) held, the molecules are copied and stay in the original project too.


## 0.213.10 — 18 November 2026

- ### 0.213.10 — The square of a button from the menus, on Mac too

A button carried out of the menus now has its light square on Mac too, like a panel button.


## 0.213.9 — 18 November 2026

- ### 0.213.9 — Dragging from the menus on Mac, reliably

On Mac a menu item now always lands where it is let go: in the column on the right or between the buttons of the top panel. Before, it was often lost on the way.


## 0.213.8 — 18 November 2026

- ### 0.213.8 — The square around a button from the menus

A button dragged from the menus onto a panel now looks like a real panel button — with the light square around its icon.


## 0.213.7 — 18 November 2026

- ### 0.213.7 — A button is not added twice

Dragging onto a panel a menu item whose button is already there now says «This button is already on the panel» instead of quietly moving it.


## 0.213.6 — 18 November 2026

- ### 0.213.6 — A line between groups of buttons

A button taken from the menus onto a panel is parted by a thin line again. And in the column on the right the line under the snapshot button is now seen.


## 0.213.5 — 18 November 2026

- ### 0.213.5 — Right click on every menu item

The right click «Add to the panel» and dragging with the mouse now work for every menu item, not only some: «To the calculation settings», «Determine the point group» and «Calculation steps», for example, can go on the panel too.


## 0.213.4 — 18 November 2026

- ### 0.213.4 — Dragging from the menus on Mac

On Mac a menu item can now really be dragged onto the panel above the model or into the column on the right — before, the menu closed and the drag broke off. And after «Add to the panel» the menu closes, so the new button is seen at once.


## 0.213.3 — 18 November 2026

- ### 0.213.3 — Every function has its own icon

Many panel buttons used to look the same: thirteen different «Save…» items with one floppy disk, eleven kinds of charges with one icon, a dozen tables and exports. Now every function has its own picture: a common sign of the action (save, open, export, remove, run) and its own object — a cell, a molecule, a table, a diagram, a folder.


## 0.213.2 — 18 November 2026

- ### 0.213.2 — A single ellipsis in the Chinese menus

In the Chinese interface seven menu items, such as «Bond style…», ended with a double ellipsis. Now they have one, like all the others.


## 0.213.1 — 18 November 2026

- ### 0.213.1 — Icons for the remaining menu items

Ten menu items that showed two letters on the panel now have icons of their own: recovering backup drafts, a new project, bond numbers, labels of selected atoms only, hiding H atoms and dummy atoms X, bond style, style of vectors and planes, van der Waals spheres and adding hydrogens.


## 0.213.0 — 18 November 2026

- ### 0.213.0 — Menu items straight onto the panel

Any menu item can now simply be dragged with the mouse onto the panel above the model or into the column on the right — it becomes a button. A right click on a menu item, «Add to the panel», works again. And several items that showed two letters on the panel got icons: isometric, perspective, axes, cell, point group.


## 0.212.5 — 18 November 2026

- ### 0.212.5 — The field reaches the line

When the right view panel folds, the dividing line now goes exactly when the field of the model has reached it, without a jump at the end.


## 0.212.4 — 18 November 2026

- ### 0.212.4 — The line of the view panel goes smoothly

When the right panel with the rotation folds, the field of the model now comes up to the dividing line and covers it, instead of the line vanishing with a jump at the end.


## 0.212.3 — 18 November 2026

- ### 0.212.3 — The projection does not go out on a second press

The «Isometry» and «Perspective» buttons in Compass no longer lose their highlight on a second press: the one in effect is always highlighted.


## 0.212.2 — 18 November 2026

- ### 0.212.2 — A calmer gold

The stars on the result button and in the project list are gone, the gold of the frame and of the ring is lighter, and the frame is thinner. Molecules with a role in the reaction are marked in the list with a gold name.


## 0.212.1 — 18 November 2026

- ### 0.212.1 — The 3D printing window and a molecule added twice

The «Model for 3D printing» window opens again. The question about a molecule that is already in the project now also comes when it has just been added and not yet saved.


## 0.212.0 — 18 November 2026

- ### 0.212.0 — The gold of the next step and result buttons by section

When a calculation ends well, the sign in the left panel gets a gold ring until the result is opened. The molecules of a project with a role in the reaction are marked in the list with a gold star, and the main result button in the calculation window with a gold frame and a star. The result buttons now depend on the section: in Compass — «Open» and «Open in Spectrum», in Spectrum — «Open in Compass» and «Open».


## 0.211.4 — 18 November 2026

- ### 0.211.4 — A tidy colour picker

The window for choosing the colour of an element or of a bond is more compact: buttons and fields of one height, no empty space in the middle.


## 0.211.3 — 18 November 2026

- ### 0.211.3 — Both sides change the angle

When three atoms are selected and a new angle is typed in the «Move the fragment» mode, both sides of the angle now turn, each by half of the change, together with their fragments. Before, only the last side moved, and for H–C–H the result was the same as in the «Move the last atom» mode.


## 0.211.2 — 18 November 2026

- ### 0.211.2 — «Fragment / angle» moves the group

In the «Fragment / angle» move mode, dragging an atom now turns its whole group (a methyl with its hydrogens, for example) about the atom it is attached to — this changes the angle. The pivot and the side can still be set by selecting two atoms.


## 0.211.1 — 18 November 2026

- ### 0.211.1 — Conformers are added without a question

The question «This molecule is already in the project» now comes only for the same structure with the same geometry. Another conformer of the same molecule is added at once.


## 0.211.0 — 18 November 2026

- ### 0.211.0 — An atom snaps to another atom

In Compass, when a new atom is drawn out with the mouse from an atom, it can be brought onto another atom or another molecule: that atom is replaced with the chosen element and bonded to the first one, and the other molecule is pulled up to the bond length.


## 0.210.4 — 18 November 2026

- ### 0.210.4 — A molecule added twice and the Russian layout

When a molecule that is already in the project (the same atoms and bonds) is added, the program asks whether to add it once more. In the «Molecule from SMILES» window, typing in Russian letters shows a hint about the keyboard layout and a button that replaces the text with Latin letters.


## 0.210.3 — 18 November 2026

- ### 0.210.3 — The sign of waiting does not press against the words

There is now some free room between the turning sign on the pill of waiting and its words.


## 0.210.2 — 18 November 2026

- ### 0.210.2 — The settings fit whole

The window «Settings» opens wide enough at once for all its fields and buttons to fit, with no cut lines and no sideways scrolling.


## 0.210.1 — 18 November 2026

- ### 0.210.1 — The check of the installation in the language of the program

The result of «Help → Check the installation…» is now in the language of the program, with me, and without the same text repeated in English «details». The sign of waiting on the pill no longer lies over the first letter.


## 0.210.0 — 18 November 2026

- ### 0.210.0 — New molecules go into the open project

A molecule by SMILES, by a name from PubChem or from the clipboard is now added to the open project as a new molecule instead of overwriting the one on the screen. The list of the molecules of a project got «Copy to a new project» and «Move to a new project» on a right click — to separate a molecule into a project of its own.


## 0.209.13 — 18 November 2026

- ### 0.209.13 — The result of the installation check and a narrow pill

«Help → Check the installation…» finally shows its result: the menu item called the check in a way that silently skipped the window with the result. A message pill is now the size of its phrase — one short line no longer stretches into a wide rectangle.


## 0.209.12 — 18 November 2026

- ### 0.209.12 — The result of the check of the installation is seen

«Help → Check the installation…» shows its result in a window in the middle of the program and briefly on the pill, for example «The installation is fine. 5/5 checks passed».


## 0.209.11 — 18 November 2026

- ### 0.209.11 — The check of the installation and the buttons of vibrations

«Help → Check the installation…» shows the window with its result again: after the change that centred windows it was lost. The buttons under a vibration in Spectrum now stand in an even row across the whole width.


## 0.209.10 — 18 November 2026

- ### 0.209.10 — A message of a molecule does not move to a crystal

A message about the result of a molecule that popped up right before going to «Compass · Crystal» no longer stays over the crystal — it goes with its subsection.


## 0.209.9 — 18 November 2026

- ### 0.209.9 — Dialogs in the middle — for real

«Settings», the questions before quitting and other dialogs opened in the top left corner: their smooth appearance took the window back to where it was before it was centred. Now a dialog appears in the middle of the window of the program.


## 0.209.8 — 18 November 2026

- ### 0.209.8 — Over a crystal — not a word about a molecule

In «Compass · Crystal» the messages about the result of a molecule of the project no longer pop up — neither that it was calculated for an earlier geometry, nor that it has atom properties. In «Compass · Molecule» and in Spectrum they stay.


## 0.209.7 — 18 November 2026

- ### 0.209.7 — The hints of the atom labels in every language

The hints of the buttons of the atom labels («1», «H», «H1») are now translated when the language changes, instead of staying Russian.


## 0.209.6 — 18 November 2026

- ### 0.209.6 — The dark theme and small things

In the dark theme the pills of messages and of the status are now dark, not light grey. A row of the list of surfaces is outlined under the mouse. The drop-down lists of the panel of the electron density have rounded corners again. «Settings» and other windows open in the middle. After switching from Chinese to Russian no Chinese words stay on buttons and in hints.


## 0.209.5 — 18 November 2026

- ### 0.209.5 — A whole map stays whole

Pressing an arrow on a map shown whole made it count as zoomed through a rounding error, and the labels of the atoms at its edge were cut. Fixed.


## 0.209.4 — 17 November 2026

- ### 0.209.4 — The journal without the blue strip

The head of the journal no longer has a blue strip at its left — it stays only on my hints. «About» in the menu «Help» now has the same «i» as the button on the panel.


## 0.209.3 — 17 November 2026

- ### 0.209.3 — The hint about the properties — once

The message «The result has atom and bond properties…» now shows once — when a result is opened or a calculation ends, not each time its tab is shown again nor after every analysis computed later.


## 0.209.2 — 17 November 2026

- ### 0.209.2 — The folder of a result in the row of the tabs

In Spectrum the button of the folder of a result moved to the row of the tabs «Result · Vibrations and IR · Wavefunction», at its right. The row over the page shows only when it holds the list of the pages or tools — «Vibrations and IR» no longer has an empty band for one button.


## 0.209.1 — 17 November 2026

- ### 0.209.1 — A pill the size of its words

A short message such as «Nothing is overlaid on the model.» no longer stretches into a wide tall pill: the pill is now the size of its words, and long messages wrap over several lines.


## 0.209.0 — 17 November 2026

- ### 0.209.0 — The menus of Compass without repeats

The menus of Compass were gone through as a whole. Repeats are gone: symmetrising is in «Tools» only, and the window that rebuilds a crystal, saving to CIF and taking molecules to a tab each have one place. «Structure comparison» — overlaying from a file and comparing with a tab — is reachable again, in «Tools». A crystal got what only a molecule could do: selecting a whole molecule, perspective, the camera, atom labels, measurements on the model, hiding atoms and a menu «Display» of its own.


## 0.208.3 — 17 November 2026

- ### 0.208.3 — «To the calculation settings» shown at once

The blue button under the model of Compass now always shows its words «To the calculation settings» («To the calculation of the crystal» for a crystal), not a bare arrow that opened under the mouse.


## 0.208.2 — 17 November 2026

- ### 0.208.2 — Marks on the axes of a profile

A profile of the wavefunction now has round values marked on both axes — the values of the function and the distance along the line, with a faint grid. When zoomed, the marks follow the part shown.


## 0.208.1 — 17 November 2026

- ### 0.208.1 — The arrows by «Build»

The arrow and zoom buttons of the map and of the profile moved from the corner of the picture to the row above it, right of «Build map» and «Build profile» — they no longer hide the labels.


## 0.208.0 — 17 November 2026

- ### 0.208.0 — Maps and profiles can be zoomed and moved

In Spectrum the maps and the profiles of the wavefunction got a small pad of arrows and zoom: a picture can be moved left, right, up and down, zoomed in and out. The mouse does the same — the wheel zooms at the pointer, a drag moves, a double click brings back the whole. On a profile the wheel with Shift stretches the values only: handy for the small values a profile is often built for.


## 0.207.2 — 17 November 2026

- ### 0.207.2 — In the middle

The pill with the summary of the calculation in Spectrum now stands in the middle, as the messages of Compass do. Dialogs open in the middle of the window of the program, not in its top left corner.


## 0.207.1 — 17 November 2026

- ### 0.207.1 — A message no longer stays behind the panels

A message that popped up in one section sometimes stayed visible behind the panels of another after switching. Now it goes with the section it appeared in.


## 0.207.0 — 17 November 2026

- ### 0.207.0 — One rule for the colour of the buttons

The buttons now follow one rule across the program. Only one button is blue — the main one of a card or a window; the rest are white, «Close» included. A switch that is pressed — such as «Remove from the model» — is light blue with a blue frame, so that it is not taken for the main action. Gold, as in the icons, comes sparingly: a gold frame marks the next step (after a calculation — «Go to Compass» or «Go to Spectrum»), and the recommended method and basis in Sextant are marked with a gold star.


## 0.206.30 — 17 November 2026

- ### 0.206.30 — A tidier panel of the electron density

The QTAIM page of the panel «Electron density» in Compass lost its second folder button — the folder in the header of the panel is enough, and now all the buttons fit. On the page «Surfaces» the buttons «Show» and «Remove» no longer run over the list of the surfaces.


## 0.206.29 — 17 November 2026

- ### 0.206.29 — «Descriptors and logK» only in the menu

After every queue the window of the calculation showed the button «Descriptors and logK…», though it makes sense only when the records carry constants. The button is gone; the window opens from «Calculation → Descriptors and logK of a queue…». The window itself now fits a laptop screen and nothing in it overlaps; when there is nothing to compare, a note stands instead of an empty plot.


## 0.206.28 — 17 November 2026

- ### 0.206.28 — One pill instead of two

When Spectrum shows the status of the calculation at the foot, messages such as «Critical points found…» no longer pop up on a second pill above it: they are added to the same pill as a line of its own. The sign of a running calculation on the left panel now stands right in the middle, in line with the other icons.


## 0.206.27 — 17 November 2026

- ### 0.206.27 — A pill instead of the line at the foot — everywhere now

The line «Tables in the folder of the calculation…» still came at the foot of the window with the panel of sections — now there too the message pops up on a pill. And while a long work runs, the pill shows the sign of its section: a sextant in Sextant, a spectrum being recorded in Spectrum.


## 0.206.26 — 17 November 2026

- ### 0.206.26 — No white strip at the foot of the window

Messages such as «Tables in the folder of the calculation…» in Spectrum and Sextant came as a line at the foot of the window and left a white strip under the page. Now, as in Compass, they pop up on a pill over the foot of the page and go by themselves.


## 0.206.25 — 17 November 2026

- ### 0.206.25 — Spectrum: the status over the panel, labels closer

The status line of Spectrum is now, as in Compass, a pill over the foot of the panel that goes by itself; there is no empty strip under the panel any more. The titles of the axes of the convergence plots stand right by their values. On the field map the scale and the size are now above the map, and the atom labels are on a light outline — seen on the dark parts too.


## 0.206.24 — 17 November 2026

- ### 0.206.24 — Convergence with axes and the status on a pill

The convergence plots now have ticks and values on their axes, axis titles along the axes, and the names of the criteria no longer lie on the curves. The number of optimization steps moved into the status line («converged in 5 steps»). The status line of Spectrum itself sits on a pill, like the messages of Compass, and goes away after a few seconds. The result tabs start after the rounded corner of the panel, «Build profile» is blue like «Build map», and atom numbers are centred in their fields.

## 0.206.23 — 17 November 2026

- ### 0.206.23 — ΔG of a reaction right from the project

Mark the reactants, transition states and products in the list of the project (right click → «Role in the reaction», a coefficient when needed) and choose «ΔG of the reaction…». The reaction diagram opens with the results of these molecules, the Gibbs energy of the reaction and the barriers. ΔG needs a calculation of frequencies of the molecules.

## 0.206.22 — 17 November 2026

- ### 0.206.22 — A tidier Spectrum

The labels of the density of states no longer lie on the curves. In QTAIM both search buttons stand side by side, and the explanation is in «?». In «Maps and profiles» each picture has its own floppy disk to save it, and the log scale is an icon. The buttons of a result have moved up, to the list of subsections. And while a calculation runs, a little spectrum is drawn beside the status line.

## 0.206.21 — 17 November 2026

- ### 0.206.21 — A subsection of a result on one panel

The title of a subsection of a result and its cards now lie on one common panel — it is seen at once that they belong together.

## 0.206.20 — 17 November 2026

- ### 0.206.20 — The pages of a result as in the panel of Compass

Over a page of a result there is now a drop-down list with its title — as the list «Optimization, Frequencies, Conformers…» in the panel of Compass. Choose another page of the same tab in it; a tab of one page has no list.

## 0.206.19 — 17 November 2026

- ### 0.206.19 — The pages of a result without a second row of tabs

In Spectrum there is now one row of tabs over a result. When a tab holds several pages — «Result ▾», for one — a click on it opens the list of their titles: choose the one you need. The second row of tabs over the page is gone.

## 0.206.18 — 17 November 2026

- ### 0.206.18 — The folder of the calculation from the panel of steps

The folder button in the panel of the steps of an optimization now opens the folder of the calculation shown — with its output file selected, whatever program computed it. It used to be called «Open ORCA result» and opened a window to choose another file.

## 0.206.17 — 17 November 2026

- ### 0.206.17 — A larger sign of a calculation

The sextant of a calculation and the compass of the search of conformers in the left panel are larger now — they are well seen beside the icons of the sections.

## 0.206.16 — 17 November 2026

- ### 0.206.16 — A sign of its own for a calculation

While a calculation of Sextant runs, the left panel now shows a sextant instead of the compass: its index arm sweeps the scale, as when one takes the height of a star, and the star flashes when it is «caught». The search of conformers is still shown by the compass.

## 0.206.15 — 17 November 2026

- ### 0.206.15 — «Rebuild the crystal» in the File menu

The item that opens the window of the CIF file again — the facts of the crystal, the block of cells, the surface — is now in «File» and is called «Rebuild the crystal (cells, surface)…». It used to stand in «Edit» under the unclear name «Crystal…».

## 0.206.14 — 17 November 2026

- ### 0.206.14 — The journal by versions

In «What's new» all the fixes of one version — 0.206.0, 0.206.1 and on — are now gathered under one heading «0.206», each under a subheading of its own. If they came out over several days, the heading shows the span of dates.


## 0.206.13 — 17 November 2026

- ### 0.206.13 — «What's new» in a straight column

In the «What's new» window every next entry moved a little further to the right, and the older ones finally went off the edge of the window. Now all the entries stand straight, one under another.


## 0.206.12 — 17 November 2026

- ### 0.206.12 — The «Project» menu without repeats

«New project with calculations…», «Open project…» and «Project molecules and calculations…» are gone from the «Project» menu of Compass — they are in the «File» menu. What stays in «Project» are the actions with the molecules of the project.


## 0.206.11 — 17 November 2026

- ### 0.206.11 — Saving only in «File»

The «Save» and «Save as…» items are gone from the «Project» menu of Compass: they repeated the same items of the «File» menu (Ctrl+S and Ctrl+Shift+S work as before).


## 0.206.10 — 17 November 2026

- ### 0.206.10 — Conformers under ☰ again

After a restart of the program the conformers found for a molecule were seen only in the «Project molecules» list. Now a molecule with conformers (and any of its conformers) has the ☰ button again with the «Conformers» page — with ΔE and shares, as right after the search.


## 0.206.9 — 17 November 2026

- ### 0.206.9 — Your own lines between buttons

A right click on a button of the row above the field or of the column on the right now offers «Part with a line on the left» or «on the right» («above» or «below» in the column) to set the button apart. If the button stands by a line, «Remove the line» is there too.


## 0.206.8 — 17 November 2026

- ### 0.206.8 — Project tabs and molecules are dragged

Project tabs can now be dragged to change their order. So can the molecules in «Project molecules»: press a row and drag it up or down — the molecule moves together with its conformers, and the new order is saved in the project.


## 0.206.7 — 17 November 2026

- ### 0.206.7 — No tooltip over the field

In the view mode the tooltip «Clicks — select · right button — reset / rotate · both buttons — pan» no longer pops up over the Compass field.


## 0.206.6 — 17 November 2026

- ### 0.206.6 — No needless gap at its own place

If you bring a dragged button to the place where it already stands, the neighbours no longer move apart and no copy appears. The copy itself is paler.


## 0.206.5 — 17 November 2026

- ### 0.206.5 — Buttons move apart

When you drag a button over a panel, the neighbouring buttons smoothly move apart to make room where it will stand — a pale copy of it is seen there. Bring it to another place and the buttons part there, while the old gap closes.


## 0.206.4 — 17 November 2026

- ### 0.206.4 — You see where a button will stand

While you drag a button over a panel, a pale copy of it and a blue line in the gap appear at the place it will take. When you bring it to another place, the copy glides there.


## 0.206.3 — 17 November 2026

- ### 0.206.3 — Panel buttons in groups

The buttons above the field and in the column on the right now stand in groups parted by thin lines. A button added from a menu stands as a group of its own at the end. Dragged among the buttons of a group it joins it without a new line, and dropped after the last button it stands after a new line (it can then be dragged to its neighbours). The lines do not repeat: there are never two in a row any more.


## 0.206.2 — 17 November 2026

- ### 0.206.2 — Buttons are dragged with the mouse

A button of the row above the field can be pressed and dragged to the column on the right — and back, and to another place in the same row. This works for the standard buttons too; «Put the buttons back as they were» returns everything to its place.


## 0.206.1 — 17 November 2026

- ### 0.206.1 — The bonds menu follows «Bond style»

The colouring and the width of bonds chosen in the «Bond style…» window changed on the model, but the checks in «View → Bond display» stayed on the old items. Now the menu shows what is chosen.


## 0.206.0 — 17 November 2026

- ### 0.206.0 — Your own buttons on the Compass panels

Any menu item can now become a button: right-click it and choose «Add to the row above the field» or «Add to the column on the right». A right click on a button of the panel removes it or moves it to the other place; the standard buttons can be removed too — they stay in the menus, and «Put the buttons back as they were» restores everything. The upright line by the column on the right is now seen when the view panel is open.


## 0.205.1 — 17 November 2026

- ### 0.205.1 — View panel: the axes in place, the labels with the atoms

When the right panel opened, the atom labels and the dashes of hydrogen bonds moved before the atoms themselves, and the drawing of the axes travelled with the model and then jumped back to the corner. Now the axes and the grid stay in their places and the labels move with the atoms. The panel button is now a single ‹› both ways, and the panel itself is set apart by a line from the column of buttons on the right.


## 0.205.0 — 17 November 2026

- ### 0.205.0 — A column of tools at the edge of the field

«Snapshot» and the buttons of what a calculation lays over the model (atoms, bonds, dipole, «Remove everything laid over») now stand in a column at the right edge of the Compass field — they are visible also when the view panel is folded, and the panel itself slides out between the field and this column. The button that folds the panel is at the end of the row above the field. The «Compare» (RMSD) button has left the row: comparison is in «View → Structure comparison».


## 0.204.15 — 17 November 2026

- ### 0.204.15 — Atom labels do not run ahead

When a panel came to rest, the atom labels were for a moment at their new places before the atoms themselves. Now the labels and the atoms appear at their new places together.


## 0.204.14 — 17 November 2026

- ### 0.204.14 — The panel slides lighter over an empty field too

After the last fix there were more frames while a panel slid. The measurement found two more needless jobs when the Compass field is empty (with Quill): at every step the styles of Quill's labels and buttons were set anew, and the empty scene was drawn. Not any more.


## 0.204.13 — 17 November 2026

- ### 0.204.13 — Less work at every frame

A measurement showed that while a panel slid, the program recomputed and redrew the decorative scales of the window and redrew the icons of all the buttons at every frame. Now the scales are a ready picture during the motion, and the icons are drawn once and then taken ready (which also speeds up redrawing throughout the program).


## 0.204.12 — 17 November 2026

- ### 0.204.12 — Panels slide with more frames

While a panel slid, the program still redrew the model under its picture and recomputed the picture itself whole — the view panel got only 5–6 frames for the whole motion. Now nothing is drawn under the picture, and the picture is cheaper — more frames, a smoother motion.


## 0.204.11 — 17 November 2026

- ### 0.204.11 — The view panel slides evenly

The right panel with the rotation buttons slid out in jerks: at every step it either stood still or jumped. Now it moves evenly.


## 0.204.10 — 17 November 2026

- ### 0.204.10 — The table heads stay in place

When conformers were folded and unfolded, the column of numbers narrowed and widened, and the heads «Structure» and «Formula» moved. Now the widths of the columns do not change.


## 0.204.9 — 17 November 2026

- ### 0.204.9 — Conformers fold smoothly

The rows of conformers in «Project molecules» no longer appear and vanish at a jerk: they grow smoothly when the group unfolds and shrink smoothly when it folds.


## 0.204.8 — 17 November 2026

- ### 0.204.8 — The project panel slides as before

The sliding of the «Project molecules» panel as pictures from 0.204.7 is gone: the panel slides again as in 0.204.6.


## 0.204.7 — 17 November 2026

- ### 0.204.7 — The project panel slides smoothly

While the «Project molecules» panel slid out, the whole window to its right was laid out and drawn again at every step — some 35 frames a second, and the tabs and buttons shook. Now during the motion a picture of the page is shown there, passing smoothly into the new arrangement, and the real buttons take their places once, when the panel has stopped.


## 0.204.6 — 17 November 2026

- ### 0.204.6 — The panel slides out without a jerk at the start

The panel used to jump a large stretch in its first moments, and the tabs and buttons beside it jerked. Now it slides out as smoothly as it slides back.


## 0.204.5 — 17 November 2026

- ### 0.204.5 — The panel slides more evenly

While a panel slides, the field shows a picture of itself — now it is only moved and not recomputed whole at every step. That recomputation made the «Molecule | Coordinates» tabs and the buttons beside them shake.


## 0.204.4 — 17 November 2026

- ### 0.204.4 — The buttons move evenly

While a panel slid in or out, the buttons beside the field crept unevenly, in jerks — at every step they moved by a pixel or stood still. Now the panel steps so that they move evenly.


## 0.204.3 — 17 November 2026

- ### 0.204.3 — The panel slides smoothly, the labels keep up

While the «Project molecules» panel (or the view panel) slid in or out, the model was drawn anew at every step and the atom labels separately over it, and they could not keep up with the atoms. Now during the motion the field moves as one picture — the model together with its labels — and the model is drawn anew once, when the panel has stopped. The motion has become lighter too.


## 0.204.2 — 17 November 2026

- ### 0.204.2 — Conformers fold, the project panel is lighter

The ▾ button of a molecule with conformers did not fold the group while that molecule itself was chosen. Now it does — and the group stays folded even when one of its conformers is shown. And the «Project molecules» panel slides in and out more lightly: the list is not read again when it closes, and every step of the motion does less needless work.


## 0.204.1 — 17 November 2026

- ### 0.204.1 — Conformers of a queue — a subgroup too

The conformers calculated by a Sextant queue went into «Project molecules» as separate rows «Conformer 1», «Conformer 2». Now they stand under their molecule and fold with it — in new calculations and in projects that already have such rows (after the project is opened again).


## 0.204.0 — 17 November 2026

- ### 0.204.0 — Bond style

«View → Bond display → Bond style…» now gathers everything about bonds: the colour (by the atoms or your own), the width, how double, aromatic and dashed bonds are drawn, long bonds dashed, and the look of hydrogen bonds. And the menu of a bond (right click) can make it aromatic, partial or coordination (dashed) and give it a colour of its own — to one bond or to all the bonds of the selected part.


## 0.203.12 — 17 November 2026

- ### 0.203.12 — The tooltips of icons are back

After the tooltips were cut down, the icon buttons (for instance «Stop» or «Put away») stopped showing theirs on hover. Now they show again — and in the conformer window every button has its own tooltip.


## 0.203.11 — 17 November 2026

- ### 0.203.11 — The conformer window changes its height at once

After «Rotation scan» the conformer window did not get lower at the first choice of another method. Now its height follows at once.


## 0.203.10 — 17 November 2026

- ### 0.203.10 — The explanations of «?» in a narrow column

The text behind «?» now runs in a narrow column with room between the paragraphs, not as one long line. And in the conformer window the fields of the method no longer run over one another.


## 0.203.9 — 17 November 2026

- ### 0.203.9 — The search methods behind «?»

There is no long description under the choice of the method in the conformer window any more: press «?» by the list — all three methods are told there. The window became more compact still.


## 0.203.8 — 17 November 2026

- ### 0.203.8 — The conformer window sized to its settings

The conformer search window now takes the height the settings of the chosen method need — no empty room and no scrolling — and there is no need to stretch it. When there are many conformers, the table scrolls.


## 0.203.7 — 17 November 2026

- ### 0.203.7 — Values in the middle of the fields

The numbers and the text in all the fields of the program now stand in the middle of the field, not at its left edge — as in the tables.


## 0.203.6 — 17 November 2026

- ### 0.203.6 — A tidier conformer window

There is no empty line under the table of conformers any more, the buttons stand right under it. And when the window is made low, the settings of the method scroll instead of running over one another.


## 0.203.5 — 17 November 2026

- ### 0.203.5 — The buttons right under the list of conformers

The row of buttons of the conformer search window is now inside the right panel, right under the table.


## 0.203.4 — 17 November 2026

- ### 0.203.4 — The buttons of the conformer window in one row

All the buttons of the conformer search window are now in one row under the list: «Search» in words, the others as icons (what an icon does shows under the pointer).


## 0.203.3 — 17 November 2026

- ### 0.203.3 — The buttons of the conformer window in their places

«Search», «Put away» and «Stop» are now under the list of conformers, on the right. Instead of a tick and a floppy disk there are buttons with words: «Take the chosen one» puts the conformer of the row into Compass, «Save XYZ…» writes all the conformers into one file.


## 0.203.2 — 17 November 2026

- ### 0.203.2 — A more visible compass of background work

The compass in the left panel is larger and stands on a «breathing» blue disc; when it is not known how much is left, a comet runs round it. The conformer search window has no «Close» button any more, and its ✕ does not cancel the search — only «Stop» does.


## 0.203.1 — 17 November 2026

- ### 0.203.1 — The conformers of a drawn molecule go to the project too

When a molecule had just been drawn and was not yet in a project, its conformers did not reach «Project molecules» after the search. Now the molecule joins a project first, and the conformers stand under it.


## 0.203.0 — 17 November 2026

- ### 0.203.0 — The compass of background work

The conformer search window can now be put away — the search goes on, and at the bottom of the left panel the needle of a compass swings; a ring fills around it while xtb refines the conformers. A click on the compass brings the window back. The same sign shows a calculation of Sextant (an hourglass used to be there); with several works their number is on it.


## 0.202.19 — 17 November 2026

- ### 0.202.19 — Spectrum messages at the foot of the window

«Tables in the calculation folder…» and similar messages of the maps, of the analysis of the states and of the charge transfer now appear for a while in the status line and take no room in the panels.


## 0.202.18 — 17 November 2026

- ### 0.202.18 — Fewer tooltips

Tooltips no longer pop up over empty places, over frames and over buttons where they repeat the words. The ones that tell something new stay: on icons without words, on the fields of settings, on cut text.


## 0.202.17 — 17 November 2026

- ### 0.202.17 — Conformers join the project under their molecule

When the molecule is in a project, the conformers found (after xtb, CREST or the bee search) appear in «Project molecules» right under it. Press ▸ and the group unfolds. In the batch mode the tick of the molecule ticks all its conformers too, and in the unfolded group you can take off those you do not need.


## 0.202.16 — 17 November 2026

- ### 0.202.16 — Orbitals can be put over one another

Show an orbital on the model and Shift+click the row of another one — it appears over the first in colours of its own (green and yellow, then violet and pink…). Another Shift+click takes it away. Handy for comparing, say, the HOMO with the orbital next to it.


## 0.202.15 — 17 November 2026

- ### 0.202.15 — A roomier electron density panel

The tree of the surfaces is in a frame with rounded corners and taller; the explanation of the difference density Δρ is behind «?» by its heading. Messages such as «Critical points found…» appear over the model for a while and take no room at the foot of the panel.


## 0.202.14 — 17 November 2026

- ### 0.202.14 — The mark of a critical point can be taken off

A chosen critical point could not be let go — its ring kept pulsing. Now the mark goes with a second click on its row, a click below the rows, Esc or a click on an empty place of the model; the points themselves stay.


## 0.202.13 — 17 November 2026

- ### 0.202.13 — A compass in the conformer window

While CREST, the bee search or xtb looks for and refines the conformers, a compass turns by the status line of the window — you can see the work is going on.


## 0.202.12 — 17 November 2026

- ### 0.202.12 — Labels and measurements with a font and a colour

«Label style» now has the font, bold and italic, the colour, an outline of the letters and the place of a label — on the atom or beside it. «Measurement style» has the font, the colours of the numbers and of the lines, and the plate. The colours are circles; ↺ puts the default colour back, and the colour picker opens in the theme of the program.


## 0.202.11 — 17 November 2026

- ### 0.202.11 — A new atom can be aimed with the mouse

In the editing mode press an atom and, holding the button, move the mouse: the new atom or fragment appears bonded to it, where you lead it. Let go, and it stays there. A plain click on an atom works as before.


## 0.202.10 — 17 November 2026

- ### 0.202.10 — The Atlas in Russian through the mirror for Russia

When the program is in Russian, «Atlas» opens on the mirror ru.azimuth-chem.com: the same pages, faster and more reliable from Russia. In English and Chinese it opens on the main address.


## 0.202.9 — 17 November 2026

- ### 0.202.9 — Numbers in the language of the program

In the English and Chinese interface the numbers of the fields are now written with a point (298.15), not a comma — «1,000 atm» is no longer read as a thousand. In Russian, still with a comma. The hint of Sextant no longer names a Russian folder: it points to the button with the folder.


## 0.202.8 — 17 November 2026

- ### 0.202.8 — Lists do not turn under the wheel

Drop-down lists no longer change their value when the mouse wheel or the trackpad is scrolled over them: the window scrolls instead. The chosen section of the left panel is now tinted see-through, and the picture of the panel shows, as on the site. The picture of Spectrum behind its section has moved into the corner, as those of Compass and Sextant.


## 0.202.7 — 17 November 2026

- ### 0.202.7 — The list of the project follows the molecule opened

When a molecule of a project is opened not from its list (from the home page, say), the list of the project now marks that very molecule. Before, «New molecule» could stay marked, and a click could not go back to it.

## 0.202.6 — 16 November 2026

- ### 0.202.6 — Style of vectors and planes

«Edit → Vectors and planes» has a «Style…»: the colour of vectors, normals and planes, the line width, the transparency of planes, the numbers, the length of a normal — and each kind can be hidden on its own. The second «Best view» left «Standard view»: «View → Best view» does the same.

## 0.202.5 — 16 November 2026

- ### 0.202.5 — «Mirror» in «Geometry», «Isometric» in «View»

«Mirror» moved from «Edit → Copy and paste» to «Edit → Geometry»: it changes the geometry rather than copying. The «View» menu has «Isometric» beside «Perspective» — always one of the two is checked.

## 0.202.4 — 16 November 2026

- ### 0.202.4 — The menu opens its windows again; the Z-matrix can be saved

«Move and turn…», «Camera position…» and «Planes of groups of atoms…» open their windows again instead of an error. «Origin at the selected atom» and «Axes on three selected atoms» put the atom at (0, 0, 0) again in a drawn molecule. The Z-matrix editor has a «Save…» button: the Z-matrix of the table is written to a text file.

## 0.202.3 — 16 November 2026

- ### 0.202.3 — Atoms, fragments and molecules

The submenu «Edit → Atoms and fragments» is now called «Atoms, fragments and molecules»: «Add a molecule» is in it too.

## 0.202.2 — 16 November 2026

- ### 0.202.2 — «Add a molecule» in Edit

«Edit → Atoms and fragments» now has «Add a molecule» and «Keep the molecule in «My molecules»…» beside «Add atom…» and «Add fragment».


## 0.202.1 — 16 November 2026

- ### 0.202.1 — A «View» button

The modes above the model got a button of their own for viewing and selecting — an arrow, first in the row. Before, you came back to viewing by releasing the pencil or the arrows; now it is plain which mode is on.


## 0.202.0 — 16 November 2026

- ### 0.202.0 — My molecules

Molecules can now be kept, as fragments are: right click on an atom — «Keep the molecule in «My molecules»…». Later it opens from «File → Example molecules → My molecules» or is put beside others through the «Molecule» menu of the building — with all its bonds. And the element chosen in the periodic table is now marked in blue, as everything in the program, not in green.


## 0.201.3 — 16 November 2026

- ### 0.201.3 — «Best view»

The button above the model that turns the molecule to a convenient side is now called «Best view», as in the View menu — so that it is not confused with «Tidy the geometry», which moves atoms. «Center» still only brings the molecule back to the middle without turning it.


## 0.201.2 — 16 November 2026

- ### 0.201.2 — The second new molecule stays too

When a project took the name of its first molecule, its folder was renamed — and the next «New molecule» was lost: the program looked for it at the old address. Now every new molecule stays in its project.


## 0.201.1 — 16 November 2026

- ### 0.201.1 — New molecules and empty projects

A molecule drawn in a new empty project no longer vanishes when you press «New molecule» — it becomes the first molecule of the project and is named by its formula, not «New molecule». The empty row «New molecule» can be removed from the list without an error. And empty projects — «+» tabs where nothing appeared — no longer leave folders in Projects.


## 0.201.0 — 16 November 2026

- ### 0.201.0 — «New molecule» adds a molecule to the project

«File → New molecule» (⌘N) no longer wipes what is on the screen. An empty row «New molecule» appears in the list of molecules of the project, the field is ready for building, and the molecule before stays where it was. As soon as you put the first atom, the row becomes a full molecule of the project; left empty, it is written nowhere.


## 0.200.3 — 16 November 2026

- ### 0.200.3 — «Delete the molecule» is always there

The item «Delete the molecule» of the atom menu (right click) is now there also when the model holds a single molecule — the model becomes empty, and «Edit → Undo» brings it back.


## 0.200.2 — 16 November 2026

- ### 0.200.2 — The folder of a saved project opens

«File → Show the file in its folder» on a tab of a saved project asked to save the project — the program did not recognise a project folder. Now Finder opens with the project file.


## 0.200.1 — 16 November 2026

- ### 0.200.1 — The mouse wheel does not change the settings

Scrolling the Settings window with the mouse wheel used to change the list or number under the pointer. That is how the scheme «Presentation» (black background) was chosen for the start without anyone noticing, and how the bond factor and the order threshold moved. Now the wheel scrolls the window, and a field changes only after a click in it. If Presentation opens for you too, choose «As last time» in «Settings → Model look», and press «Defaults» in «Bonds and steps».


## 0.200.0 — 16 November 2026

- ### 0.200.0 — A home page without the greeting, the Atlas apart

Quail and her greeting have left the home page: right under the name you now see what Azimuth is, then Continue and the sections. Quail has not gone anywhere — she is in the question windows, the hints of Compass and on the site.

In the left panel a line sets the Atlas apart from the sections of the program, and its button has an arrow ↗: it opens on the site, in the browser.


## 0.199.4 — 16 November 2026

- ### 0.199.4 — Quill at full height in the question windows

In windows such as «Unsaved project» Quill now stands at the left the whole height of the window, with the question and the buttons to her right. The window is no taller: Quill fits the text, not the text her.

## 0.199.3 — 16 November 2026

- ### 0.199.3 — The compass of waiting as on the icon

The compass that turns while the program or the site is calculating is now drawn as on the icon of Azimuth: the same divisions on the ring, the same needle, the same thickness of the arc. There is no star — nothing for the needle to settle on, so it keeps turning.

## 0.199.2 — 16 November 2026

- ### 0.199.2 — A drawn molecule at the centre of its coordinates

The first atom put in the empty field is the origin (0, 0, 0) wherever you click; then the origin is the middle of the bond, then the centre of the whole molecule, and the view turns about it. The model does not jump on the screen. A molecule from the library appears where you click. A structure opened from a file keeps its coordinates.

## 0.199.1 — 16 November 2026

- ### 0.199.1 — Quill stands on the floor

Under Quill's feet and the things beside her there is now a hatched floor, as in a book illustration: she no longer hangs in the air. So in every window of the program, on the home page of the site and in the Atlas.

## 0.199.0 — 16 November 2026

- ### 0.199.0 — IGMH: who interacts with whom

A new analysis of the weak interactions between molecules — IGMH. Its surface shows only what lies between the molecules, and a table tells which atom pairs give the interaction the most: in the water dimer almost half comes from the H···O pair of the hydrogen bond.

## 0.198.0 — 16 November 2026

- ### 0.198.0 — NCI names the interactions

Under the NCI plot there is now a table: every spot of the surface is its own row with its kind (hydrogen or halogen bond, C–H···π, π stacking, van der Waals contact, repulsion), its atoms and its strength. The number of the row stands both over the dip of the plot and at the spot on the model.

## 0.197.1 — 15 November 2026

- ### 0.197.1 — divisions on the compass

The ring of the waiting compass now has its divisions, as on the icon of the program.

## 0.197.0 — 15 November 2026

- ### 0.197.0 — the compass with inertia

While the program waits, the compass now starts slowly, speeds up, slows down and stops at the north — twice: on the first turn it draws the golden arc, on the second it takes it back.

## 0.196.0 — 15 November 2026

- ### 0.196.0 — the name like the icon

The letter A now holds the needle of the compass, Z ends in an arrow like the golden arrow of the icon, and the star is golden.

## 0.195.0 — 15 November 2026

- ### 0.195.0 — Quail looks to the left

Quail with the magnifier in the empty Spectrum and Quail counting a calculation now face to the left.

## 0.194.0 — 15 November 2026

- ### 0.194.0 — Azimuth on Linux

The program can be installed on Linux (x86_64, Ubuntu 22.04 and newer): `./Launch-Linux.sh` in a terminal, and `./Launch-Linux.sh --install-desktop` adds it to the menu of applications.

## 0.193.1 — 15 November 2026

- ### 0.193.1 — fewer molecules, scattered

There are fewer drawings on the left panel, they are scattered more freely and do not go above the line under the name.

## 0.193.0 — 15 November 2026

- ### 0.193.0 — molecules all along the panel

Thin drawings of molecules now run in the background of the left panel — from the name down to the very bottom, both in the narrow rail and in the open part; three cells of crystals are among them.

## 0.192.6 — 15 November 2026

- ### 0.192.6 — the same proportions

The cards of the Spectrum of a crystal share the width as those of a molecule: the table two parts, the plots three.


## 0.192.5 — 15 November 2026

- ### 0.192.5 — the Spectrum of a crystal as that of a molecule

The Spectrum of a crystal is now built as that of a molecule: the tabs on the top of the frame, the table of the steps on the left, the plots of the optimization on the right, and for an energy or before any calculation — Quill with a hint; the calculation and its result are at the foot. Switching the tabs of the projects in Spectrum no longer takes you to Compass.


## 0.192.4 — 15 November 2026

- ### 0.192.4 — the Atlas in the theme of the program

The item «Atlas» opens the site in the same theme as the program: a dark site from a dark program, a light one from a light. The site keeps it, as if it had been chosen with its switch.


## 0.192.3 — 15 November 2026

- ### 0.192.3 — an energy has a tab too

An energy calculation of a crystal opened in Spectrum as an empty frame: only an optimization had a tab. Now the first tab «Energy and steps» is always there — for an energy it holds a row with the energy and the cell, for an optimization the plots and the steps.


## 0.192.2 — 15 November 2026

- ### 0.192.2 — just as for a molecule

The empty Spectrum of a crystal is now arranged exactly as that of a molecule: a tab at the top, and in it me with my magnifier and a hint.


## 0.192.1 — 15 November 2026

- ### 0.192.1 — the empty Spectrum of a crystal

While a crystal has no calculations, Spectrum looks as it does for a molecule: me with my magnifier in the middle and a hint where to compute.


## 0.192.0 — 15 November 2026

- ### 0.192.0 — continue with a crystal

The home page now has two Compass cards: «Molecule» and «Crystal» — each brings back its own last work. And if the last file is already gone, the card does not disappear but takes the newest of the recent ones.


## 0.191.0 — 15 November 2026

- ### 0.191.0 — I got smaller

In question windows I am small now and stand beside the headline, and the text runs under us the whole width — the windows are no longer empty. And the blue strip stayed only on my tip clouds; I took it off the windows.


## 0.190.0 — 15 November 2026

- ### 0.190.0 — delete a whole molecule

When the model has several molecules, a right click on any atom now offers «Delete the molecule» — the whole molecule of that atom goes, the others stay. Changed your mind — «Edit → Undo».


## 0.189.2 — 15 November 2026

- ### 0.189.2 — even fields

The fields of the crystal calculation setup now stand exactly where those of a molecule do. And in the program list of a new project a thin line, not an empty row, separates the programs for molecules from those for crystals.


## 0.189.1 — 15 November 2026

- ### 0.189.1 — a drawn molecule is not lost

If you drew a molecule outside a project and went to another tab, the «New project» tab sometimes vanished. Now, when you leave, the molecule is written into a draft project at once, and its tab stays in place.


## 0.189.0 — 15 November 2026

- ### 0.189.0 — antiferromagnets

NiO, MnO, FeO are antiferromagnets: half of the metal atoms point their spin up, half down. Now this is switched on in «Additional settings…»: a spin-polarized calculation, the order antiferromagnetic. The program splits the atoms into two sublattices itself and says if the cell is too small for that. And if such a crystal is started without spin, Quail asks whether it is meant so.


## 0.188.2 — 15 November 2026

- ### 0.188.2 — the settings of one crystal

The U of nickel from a NiO calculation no longer passes to the silicon of the next tab and no longer blocks the run: when the crystal changes, only the U of its own elements stay, and the cell charge goes back to zero.


## 0.188.1 — 15 November 2026

- ### 0.188.1 — tabs during a calculation

If you open another crystal tab during a calculation, Sextant no longer mixes up the picture: the page keeps the crystal being computed, with a line saying why. When the calculation ends, the page goes to the crystal of the open tab by itself.


## 0.188.0 — 15 November 2026

- ### 0.188.0 — a crystal is set up like a molecule

The calculation setup of a crystal is now arranged as that of a molecule: name, program, task, method, basis set, dispersion, resources — in the same order and in the same places. The cell charge, spin, DFT+U and the SCF settings went to «Additional settings…» at the bottom of the card.


## 0.187.0 — 15 November 2026

- ### 0.187.0 — crystal analysis — in Compass

Sextant sets up and runs a calculation, and it is examined in Compass and Spectrum — for a crystal now as for a molecule. The Multiwfn buttons left the Sextant page; after a calculation «Go to Compass» and «Go to Spectrum» appear: the charges and the AIM bonds are there.


## 0.186.2 — 15 November 2026

- ### 0.186.2 — the buttons wrap

After a CP2K calculation the Multiwfn buttons and the long file path stretched the right part of the crystal page, and the settings on the left were squeezed. Now the buttons go to a second row, and the file name stands instead of the path.


## 0.186.1 — 15 November 2026

- ### 0.186.1 — CP2K computes again

Since 13 November CP2K refused to read the input file: version 2026.2 moved the projected density of states to another section, and the program wrote it the old way. Fixed — crystal calculations in CP2K start, and the PDOS is printed again.


## 0.186.0 — 15 November 2026

- ### 0.186.0 — GFN1-xTB for crystals

In CP2K you can now choose GFN1-xTB — a semiempirical method hundreds of times faster than DFT. Handy to optimize a large cell of a molecular crystal roughly first and refine it with PBE afterwards.


## 0.185.0 — 15 November 2026

- ### 0.185.0 — hybrid functionals

PBE0 and HSE06 appeared in Quantum ESPRESSO. They give the band gap more honestly — PBE underestimates it noticeably — but take tens of times longer. The energy only for now: pw.x cannot do the forces and the optimization of hybrids with the SSSP pseudopotentials.


## 0.184.0 — 15 November 2026

- ### 0.184.0 — DFT+U

For transition-metal oxides PBE nearly closes the gap — for NiO, MnO and FeO it comes out near zero. Now the «DFT+U» line takes a U for a d or f shell: «Ni 6.2» — and both Quantum ESPRESSO and CP2K get the Hubbard correction. Take the value of U for the same program: it depends on the projectors.


## 0.183.0 — 15 November 2026

- ### 0.183.0 — the functionals of CP2K

CP2K got a choice of functional too: PBE, PBEsol, revPBE and BLYP; the D3 correction follows the one chosen. DZVP-MOLOPT and TZVP-MOLOPT joined the basis sets. And a mistake is fixed: TZV2P was offered for sodium, magnesium and aluminium, but CP2K has none for them.


## 0.182.0 — 15 November 2026

- ### 0.182.0 — new functionals for crystals

For Quantum ESPRESSO a functional can now be chosen: PBEsol when exact lattice parameters matter, or the non-local vdW-DF2, rev-vdW-DF2, vdW-DF-cx and rVV10 — they include dispersion themselves, for molecular and layered crystals. The Tkatchenko–Scheffler and MBD corrections were added, and a cell can be given a charge — in both QE and CP2K.


## 0.181.0 — 14 November 2026

- ### 0.181.0 — what the energy of a pair is made of

The pair energies of a crystal are now split into electrostatics, dispersion, repulsion and the rest — you see at once where a hydrogen bond holds and where a stack of rings. And salts are no longer taken as neutral: the window recognizes the ions by the formula and lets you correct the charges.


## 0.180.0 — 14 November 2026

- ### 0.180.0 — COD search by cell

The COD window searches by the cell parameters too: «As the open one» puts in the cell of the crystal from Compass, and the database finds the same structure in other works — or a similar phase.


## 0.179.0 — 14 November 2026

- ### 0.179.0 — anomalous scattering

The diffraction pattern window has the checkbox «Anomalous scattering»: the atoms scatter with the f′ and f″ corrections at the line of the chosen tube. For organic compounds the difference is hardly seen, but iron with a cobalt tube changes the intensities noticeably.


## 0.178.0 — 14 November 2026

- ### 0.178.0 — click a bond

The dashed line of a hydrogen bond on the model now answers a click: its atoms, length and angle appear at the bottom, and in an open «Contacts» window its row is selected.


## 0.177.0 — 14 November 2026

- ### 0.177.0 — what P2₁/c means

The Crystal window has the button «What does … mean»: it takes the space-group symbol apart letter by letter — which lattice, where the screw axis is and where the plane glides. And the checkbox «Bravais lattice nodes» shows the lattice itself on the model — with the centring nodes.


## 0.176.0 — 14 November 2026

- ### 0.176.0 — a molecule can be printed

«File → Model for 3D printing…» saves what Compass shows — a molecule, a piece of a crystal with the cell edges — as balls and sticks for a 3D printer: STL or coloured VRML. A model for a class that you can hold in your hands.


## 0.175.0 — 14 November 2026

- ### 0.175.0 — the shape of the Hirshfeld surface

The Hirshfeld surface can now be coloured by the shape index and the curvedness. Bumps are blue, hollows where a neighbour atom fits in are red; red-and-blue «bow ties» give away a π–π stack, and the curvedness shows the flat faces by which molecules lie on one another.


## 0.174.1 — 14 November 2026

- ### 0.174.1 — crystals too

An opened CIF that was not computed no longer leaves a folder in «Projects/Crystals» after it is closed.


## 0.174.0 — 14 November 2026

- ### 0.174.0 — look and not keep

Opened a molecule just to look — after closing it leaves no trace in «Projects»: a project is kept only if you changed or computed something in it. And the point group can now be found in the «Tools» menu too, without hunting for the button in the corner.


## 0.173.2 — 14 November 2026

- ### 0.173.2 — a hint of the diffraction pattern

If the indices of the preferred orientation are written wrongly, the diffraction pattern window now says so — the hint is no longer lost under the line of the comparison with experiment.


## 0.173.1 — 14 November 2026

- ### 0.173.1 — small things from a tester's report

The arrows at the top left say that they switch the sections, and undoing an edit is ⌘Z. A molecule stays noticeably sharper while it is turned and zoomed. After the calculation programs are installed you see the folder they went to.


## 0.173.0 — 14 November 2026

- ### 0.173.0 — the theme as in the system

«Settings → Theme» has the choice «As in the system»: the program becomes light or dark together with macOS or Windows — by day and by night by itself. The theme button of the left panel still switches by hand.


## 0.172.2 — 14 November 2026

- ### 0.172.2 — simple molecules in the examples

«File → Open an example…» has a folder 0-molecules: water, methane, ammonia and benzene — to get to know Compass starting from the simplest. Their point groups are C₂v, T_d, C₃v and D₆h.


## 0.172.1 — 14 November 2026

- ### 0.172.1 — after the first tester's report

Thanks to the first tester! No more error window when the pointer is over «Atom labels»; ORCA inputs with atomic numbers instead of symbols open; after a change of language the headings of the task settings, «procs», «MB», «cycles» and the «New project» tab are translated too. And an error report no longer holds macOS's own settings — only those of the program.


## 0.172.0 — 14 November 2026

- ### 0.172.0 — pair energies and the framework

«Crystal → Pair energies and framework (xtb)…»: how strongly a molecule is bound to each neighbour, the lattice energy and the «energy framework» on the model — thick blue lines between the centres of the molecules show where the crystal has strong columns, layers or a 3-D network. Calculated in xtb in seconds.


## 0.171.0 — 14 November 2026

- ### 0.171.0 — crystals from COD

«File → Find a crystal in COD…» in «Compass · Crystal» searches the Crystallography Open Database — an open collection of nearly half a million structures — by words, a formula or elements, and opens the CIF found with one click. It is an open database, free to use. An internet connection is needed; only the search criteria are sent.


## 0.170.0 — 14 November 2026

- ### 0.170.0 — the network by layers

The contact network of the Contacts window can now be grown layer by layer and built only from the selected rows of the table: you see where a chain or a layer of one chosen bond goes.


## 0.169.0 — 14 November 2026

- ### 0.169.0 — the Hirshfeld surface

«Crystal → Hirshfeld surface…»: a molecule inside its surface, with red spots where neighbours come closer than the van der Waals radii (hydrogen bonds are seen at once), and the fingerprint plot — which contacts at which distances make up its surroundings. For benzoic acid: H···H 42 %, O···H 25 %, C···H 22 %.


## 0.168.0 — 14 November 2026

- ### 0.168.0 — a pattern closer to the instrument

In the powder pattern window you can now add the second line of the tube, Kα₂ — the peaks split in two, as on a real copper tube; set the peak widths by Caglioti so that they widen towards high angles, and the step of the curve; and take texture into account by March–Dollase — when plates lie flat in the holder and some peaks are higher than they should be. The comparison with a measured pattern uses the same peak shape.


## 0.167.0 — 14 November 2026

- ### 0.167.0 — an error can be sent to the author

If something breaks, the error window has a button «Send to the author…»: the program saves the report to the desktop and opens a ready e-mail — you only attach the file and write a few words about what you were doing.


## 0.166.0 — 14 November 2026

- ### 0.166.0 — Azimuth in one file

The Mac now has a disk image: «Azimuth» is dragged into «Applications» and opens like any application — without Python and a folder of sources. Windows already had such an installer. The builds are not signed yet: at the first start the system will ask whether you trust the program.


## 0.165.0 — 14 November 2026

- ### 0.165.0 — the network of stacks

«Show the network» in «Contacts» can build the network not only from hydrogen and halogen bonds but also from π–π stacks and C–H···π: you see how the rings pile up into columns and a «herringbone».


## 0.164.0 — 14 November 2026

- ### 0.164.0 — second-level graph sets

«Contacts» has a second table: which patterns hydrogen bonds of two different kinds make together. Two independent acid molecules that give only D and D apart close the familiar R²₂(8) ring together; the bonds that link the dimers show as second-level chains and rings.


## 0.163.1 — 14 November 2026

- ### 0.163.1 — a new address for letters

You can now write to the author at contact@azimuth-chem.com — it is shown in «About» and on the site.


## 0.163.0 — 14 November 2026

- ### 0.163.0 — the molecular shell

«Crystal → Molecular shell…» puts a molecule and all its neighbours on the model — those closer than a given distance or touching it with their van der Waals spheres. Their number is the molecular coordination number (14 within 4 Å for benzoic acid), and the table gives each neighbour its symmetry code and shortest contact. The centre is the molecule whose atom is selected on the model.


## 0.162.0 — 14 November 2026

- ### 0.162.0 — hydrogen bonds as in a paper

The «Contacts» window of a crystal has a button «Table for a paper…»: the hydrogen bonds with the lengths D–H, H···A, D···A, the angle and the symmetry code of the acceptor (for example, «−x+1, −y, −z+1» for the dimer of benzoic acid); you can copy it straight into your text or save it to CSV. And the criteria of the contact search are now yours to set: the margin over the sum of the radii and the smallest angles of the bonds.


## 0.161.0 — 14 November 2026

- ### 0.161.0 — the program got lighter

The Atlas has moved to the site for good: its window and the built-in Chromium browser are gone from the program, so a new installation is much smaller. The «Atlas» item still opens it on the site.


## 0.160.1 — 13 November 2026

- ### 0.160.1 — «Back» no longer stops by Compass

If you go from Sextant to «Compass · Crystal», the «Back» button now returns to Sextant, not to Compass with a molecule.


## 0.160.0 — 13 November 2026

- ### 0.160.0 — the Atlas moved to the site

The Atlas now lives on the site azimuth-chem.com: the «Atlas» item of the panel and its card on the home page open it in a browser, in the language of the program. «Open in Compass» on a topic page still opens the molecule here. My tips stayed on the site, and «Continue» with the last topic is at the start of the Atlas overview. Many sections of the manual now link to the right topics of the Atlas.


## 0.159.0 — 13 November 2026

- ### 0.159.0 — frequencies and critical points of a crystal

The Γ-point frequencies (CP2K) are in the «Frequencies» left panel, and the atoms of the crystal move as in a molecule; the AIM critical points are on the model of the crystal. Closing the last project no longer switches to «Molecule».


## 0.158.1 — 13 November 2026

- ### 0.158.1 — a smooth waiting compass

The golden arc of the waiting compass now fills during one turn of the needle and empties just as smoothly during the next — without a jump.


## 0.158.0 — 13 November 2026

- ### 0.158.0 — comparing packings and hkl planes

«Crystal → Compare the packing…» tells whether two files (or an experiment and a calculation) have the same packing; «Planes (hkl) in the cell…» shows the reflecting planes on the model, also on a double click on a line of the powder pattern.


## 0.157.0 — 13 November 2026

- ### 0.157.0 — hydrogens, cell setting, planes

Contacts are found with the H atoms at neutron distances; «Crystal → Cell setting…» shows the crystal in another setting of the group (P 21/c ↔ P 21/n) or in the reduced cell; planes through groups of atoms work in «Crystal» too.


## 0.156.0 — 13 November 2026

- ### 0.156.0 — comparison with an experimental powder pattern

An experimental powder pattern is now compared with the calculated one: the background is subtracted, the zero shift and the change of the cell are fitted, and you see which lines are found, which are missing and which peaks are extra (an impurity).


## 0.155.0 — 13 November 2026

- ### 0.155.0 — the shape of a crystal

«Crystal → Crystal shape (BFDH)…»: the faces of a crystal from its interplanar spacings — why salt grows as octahedra and cubes and benzoic acid as plates.


## 0.154.0 — 13 November 2026

- ### 0.154.0 — voids of a crystal

«Crystal → Voids…»: where a solvent molecule fits in a crystal — the volume, the cavities and channels, a surface on the model.


## 0.153.1 — 13 November 2026

- ### 0.153.1 — icons of the crystal buttons

The Multiwfn and PDOS buttons on the crystal pages show their icons again.


## 0.153.0 — 13 November 2026

- ### 0.153.0 — exporting a crystal

«File → Export the crystal»: POSCAR for VASP, extended XYZ for ASE and OVITO, a block of cells in CIF (P 1); «File → Save the picture» takes pictures of a crystal as of a molecule.


## 0.152.0 — 13 November 2026

- ### 0.152.0 — density and ELF of a crystal

«Compass · Crystal» has «Calculation → Electron density on the model» and «ELF on the model»: a surface from the CP2K wave function over the whole model of the crystal.


## 0.151.0 — 13 November 2026

- ### 0.151.0 — PDOS of a crystal

The Spectrum of a crystal has the density of states projected on the elements and on s, p, d (CP2K and Quantum ESPRESSO); for earlier CP2K calculations it is computed from the wave function. In Compass — «Calculation → Density of states (PDOS)».


## 0.150.0 — 13 November 2026

- ### 0.150.0 — the Brillouin zone and crystal labels

«Crystal → Brillouin zone…» — the first zone, the high-symmetry points and the band path, turned with the mouse. «Crystal → Labels on the model» — oxidation states, bond valence sums, fractional coordinates, multiplicity and site symmetry on the atoms.


## 0.149.0 — 13 November 2026

- ### 0.149.0 — analysis of a crystal structure

«Crystal → Structure analysis»: the Madelung energy (formal charges or CM5 charges of a calculation), bond valence sums, Shannon radii and Pauling's rules, the Goldschmidt factor, the packing of ions and a comparison of the optimized cell with the experiment.


## 0.148.0 — 13 November 2026

- ### 0.148.0 — crystal menus

«Compass · Crystal» has new menus «Crystal» (facts, a block of cells, view, contacts, powder pattern) and «Calculation» (Sextant, optimization steps, charges, AIM bonds, Spectrum) — with icons.


## 0.147.1 — 13 November 2026

- ### 0.147.1 — the compass in the waiting note

The compass with its needle is now also in the note of long operations with «Esc — cancel».


## 0.147.0 — 13 November 2026

- ### 0.147.0 — a crystal in Compass and Spectrum

The atomic charges of a crystal (CM5, Hirshfeld) are now written right on the model in Compass, as for a molecule. Spectrum shows crystal calculations: the optimization plots (the energy and the cell by steps), bands and density of states, charges and AIM bonds.


## 0.146.2 — 13 November 2026

- ### 0.146.2 — crystal analysis buttons

The crystal page of Sextant has the buttons «Bonds by AIM» and «Charges» for a CP2K calculation.


## 0.146.1 — 13 November 2026

- ### 0.146.1 — the crystal page

Sextant chooses the program of the last crystal calculation by itself and shows its summary with the analysis buttons; the formula in the card is the crystal's (CsCl), and «auto» in the occupations says whether it is an insulator or a metal.


## 0.146.0 — 13 November 2026

- ### 0.146.0 — calculations in a crystal project

An opened crystal project shows the steps of its last optimization at once — you can page through them and take the optimized cell, as after the calculation.


## 0.145.1 — 13 November 2026

- ### 0.145.1 — choosing a project file

«Open project…» again lets you choose the project file project.qcc, opening right in the folder of molecular or crystal projects.


## 0.145.0 — 13 November 2026

- ### 0.145.0 — a compass instead of a spinner

While the program calculates or loads, the compass from the Azimuth logo turns instead of an arc: the needle sways like a real compass's, and the golden azimuth arc follows it.


## 0.144.0 — 13 November 2026

- ### 0.144.0 — a project names itself

If a project has not been named, it is called after its first molecule — «Water», «Water and 2 more» — and so is its folder. A name given when saving stays.


## 0.143.1 — 13 November 2026

- ### 0.143.1 — project folders

«Open project…» opens the usual file dialog right in the folder of projects: molecular projects now lie in «Проекты/Молекулы», crystal ones in «Проекты/Кристаллы». The extra «This computer» window that appeared at start is gone.


## 0.143.0 — 13 November 2026

- ### 0.143.0 — the «Open project» window

«Open project…» shows the folder of projects at once: molecular and crystal projects on separate tabs, with their contents and the date of change; empty drafts are hidden.


## 0.142.1 — 13 November 2026

- ### 0.142.1 — projects from the crystal mode

The «File» menu of «Compass · Crystal» has «Open project…», «New research project…» and «Recent files»; the «Open CIF…» dialog accepts projects too.


## 0.142.0 — 13 November 2026

- ### 0.142.0 — atomic charges of a crystal

After a CP2K calculation you can compute the atomic charges (CM5 and Hirshfeld) in Multiwfn. The summary of the last crystal calculation is seen after a restart of the program too, together with the analysis buttons.


## 0.141.0 — 12 November 2026

- ### 0.141.0 — AIM bonds of a crystal

After a crystal calculation in CP2K the button «Bonds by AIM» runs Multiwfn and shows a table of bonds: the length, the number of bonds of an atom, the density at the critical point and the type of interaction. In CsCl the Cs–Cl bond comes out ionic, as it should.


## 0.140.1 — 12 November 2026

- ### 0.140.1 — a crystal wave function for Multiwfn

After a CP2K calculation Azimuth prepares a wave function file that Multiwfn reads as a periodic system: with the cell and the charges of the pseudopotentials.


## 0.140.0 — 12 November 2026

- ### 0.140.0 — crystal optimization step by step

The optimization steps of a crystal are seen in Compass as for a molecule: where the atoms were and where they went, the RMSD and the change of the cell. «Take» brings back the symmetry of the original crystal. For a small cell CP2K takes a supercell by itself, and salts are no longer treated as metals.


## 0.139.1 — 12 November 2026

- ### 0.139.1 — optimization with the cell in CP2K

An optimization with the cell no longer stops at the input file in CP2K 2026; CP2K errors appear in the calculation card in plain words.


## 0.139.0 — 12 November 2026

- ### 0.139.0 — the progress of a crystal calculation

During a CP2K or Quantum ESPRESSO calculation the card shows the SCF step, the energy and the optimization step; CP2K always saves the wave function (.molden) for analysis in Multiwfn.


## 0.138.9 — 12 November 2026

- ### 0.138.9 — CP2K checked with a real calculation

The first CP2K calculation on a Mac is read correctly. «+» in «Compass · Crystal» no longer switches to «Molecule», and Spectrum opened from a crystal project no longer makes an empty project.


## 0.138.8 — 12 November 2026

- ### 0.138.8 — the server window does not freeze on a slow DNS

The check «does the server answer?» keeps to its time even when the name lookup is slow.


## 0.138.7 — 12 November 2026

- ### 0.138.7 — a crystal opens faster

The check of the space group of a CIF file is done in integers instead of fractions — the same result several times faster.


## 0.138.6 — 12 November 2026

- ### 0.138.6 — the window opens faster

The style of the window is applied once at start, not twice.


## 0.138.5 — 12 November 2026

- ### 0.138.5 — a molecule tab without a project does not vanish

A molecule not yet saved into a project keeps its «New project» tab both in «Compass · Crystal» and in Sextant; a click on it brings you back to the molecule.


## 0.138.4 — 12 November 2026

- ### 0.138.4 — a project has no kind until its first file

A new project has no icon while it is empty; Sextant offers it both the molecular programs and Quantum ESPRESSO / CP2K for a crystal — choosing the latter opens a CIF.


## 0.138.3 — 12 November 2026

- ### 0.138.3 — CP2K on a Mac from the install menu

On a Mac CP2K is installed from «Install calculation programs…» through Homebrew; Homebrew itself is needed (brew.sh). There is no CP2K build for Windows — crystals are calculated on a server.


## 0.138.2 — 12 November 2026

- ### 0.138.2 — the icon of a project's kind

The project tab shows what is inside: a molecule or a crystal icon.


## 0.138.1 — 12 November 2026

- ### 0.138.1 — crystal and molecule projects apart

Going to «Compass · Molecule» from a crystal project opens a «New project» — the molecule does not get into the crystal project. Sextant shows the programs by the kind of project: for a crystal Quantum ESPRESSO and CP2K, for molecules ORCA and the others. The CP2K fields no longer run over each other.


## 0.138.0 — 12 November 2026

- Crystals have a second program — CP2K. It calculates with Gaussian basis sets and plane waves at the Γ point and is faster than Quantum ESPRESSO on large cells, for example on molecular crystals. It is chosen in the «Program» line of the crystal calculation page. On Linux and on a server CP2K is installed from the program, on a Mac through Homebrew (brew install cp2k).

## 0.137.0 — 11 November 2026

- Sextant for a crystal now looks the same as for molecules: on the left the calculation setup with the Quantum ESPRESSO settings (k grid, cutoffs, smearing, D3 correction, spin, supercell), on the right the crystal and the start, below the input file, and during the calculation — me, Quail, with its progress. Every open crystal becomes a project of its own, with its tab and a folder where its calculations are kept.

## 0.136.2 — 11 November 2026

- Atlas: the demonstration of the Hückel method no longer stops with an error, and the demonstration of vibrations really shows the degenerate vibration of SF₆ in its last step.

## 0.136.1 — 11 November 2026

- After a change of theme the tabs are no longer cut, and no scroll arrows appear next to them.

## 0.136.0 — 11 November 2026

- Quantum ESPRESSO calculations can be sent to a server: the calculation window has the choice «Where» — this computer or a server from «Server…». The program puts the pseudopotentials into the calculation folder itself, queues the job in SLURM and shows its progress, as for ORCA. This works on Windows too, where there is no Quantum ESPRESSO build of its own.

## 0.135.0 — 11 November 2026

- Quantum ESPRESSO now calculates the band structure and the density of states of a crystal: the program builds the path through the high-symmetry points of the Brillouin zone itself, and the plots open with a button after the calculation. Silicon gets a gap of about 0.57 eV — just what the PBE functional gives (the experiment is 1.12 eV).

## 0.134.0 — 11 November 2026

- The «Contacts» of a crystal now tell type I halogen contacts from type II ones: only type II, when the σ-hole of one atom faces the belt of the other, counts as a true halogen bond. The table got the normalized distance d/Σr and the angles θ1, θ2, and «Show the network» can build a network of halogen and other σ-hole bonds, not only hydrogen bonds.

## 0.133.1 — 11 November 2026

- The examples have a molecular crystal — benzoic acid from the open COD database: it shows O–H···O hydrogen bonds, the R²₂(8) dimer and displacement ellipsoids («File → Open an example…» → 10-crystals).

## 0.133.0 — 11 November 2026

- Quantum ESPRESSO is in Sextant: the list of programs has «Quantum ESPRESSO (crystal)», and the arrow at the bottom of «Compass · Crystal» leads straight to the calculation of the open crystal. You can still take single molecules out of a crystal: select their atoms and press the same arrow.

## 0.132.1 — 11 November 2026

- While calculation programs are being installed, the Sextant window shows the installation itself, not «No calculation yet…».

## 0.132.0 — 11 November 2026

- A Quantum ESPRESSO crystal calculation runs in the primitive cell by default: centred lattices (as in NaCl and silicon) have four times fewer atoms, and the energy per formula unit is the same — the calculation is many times faster.

## 0.131.0 — 11 November 2026

- The «Open in Compass» buttons are now on the Atlas topics on the site too: press one, and the molecule opens in the installed program. The first time, the browser will ask permission to open Azimuth.

## 0.130.0 — 11 November 2026

- A crystal can now be calculated in Quantum ESPRESSO right from Compass: the window «Calculation in Quantum ESPRESSO…» writes the input file, runs pw.x, shows the energy, the pressure and the gap, and after an optimization opens the new cell. For example, an optimization of silicon with PBE gives a lattice constant of 5.47 Å (the experiment is 5.43).

## 0.129.0 — 11 November 2026

- Installing Quantum ESPRESSO now also downloads the SSSP pseudopotential library, and the program can write a pw.x input file for a crystal (the cell, the atoms, k-points by the size of the cell, cutoffs from the library). Running it from Sextant is the next step.

## 0.128.0 — 11 November 2026

- «Install calculation programs» can now install Quantum ESPRESSO too — a program for plane-wave calculations of crystals (macOS and Linux) — into a separate folder, so that its Open MPI does not get in the way of ORCA. This is the first step towards periodic calculations.

## 0.127.0 — 11 November 2026

- Sextant has a new task «Interaction energy with BSSE (two molecules)»: for a pair of molecules — for example, one cut out of a crystal — the program sets up five ORCA calculations by itself and gives the interaction energy with the Boys–Bernardi counterpoise correction for basis set superposition.

## 0.126.0 — 11 November 2026

- The «Contacts» window of a crystal now finds C–H···π contacts too, and the box «Rings, π–π and C–H···π on the model» in the menu «View of the crystal» shows the ring planes, their centroids, the stacks and C–H···π right on the model.

## 0.125.0 — 11 November 2026

- A crystal can be built not only from whole cells but also by a range of coordinates (for example −0.5…1.5 along a), and the molecules can be coloured by the symmetry operation that makes them: so you see the «herringbone» of a screw axis and the layers of a glide plane.

## 0.124.0 — 11 November 2026

- The «Contacts» window of a crystal now finds the flat rings of molecules and π–π stacks between them: the distance between the centroids, the angle between the planes, the distance to the plane and the offset of the rings.

## 0.123.0 — 11 November 2026

- In the «Contacts» window of a crystal the hydrogen bonds got an Etter graph set: D, S(n), C(n) or R(n) with the numbers of acceptors and hydrogens — for example, R²₂(8) for a carboxylic acid dimer and C(2) for a chain of water molecules.

## 0.122.0 — 11 November 2026

- The «Coordinates» tab of a crystal has a new format «Fractional (CIF)»: the atoms of the model in fractions of the cell with the labels and occupancies from the file — a ready CIF of the block shown, which you can copy or save.

## 0.121.0 — 11 November 2026

- Switching between the light and the dark theme is several times faster: the program no longer restyles every element of the interface anew, but keeps both themes in one style sheet and changes only the mark of the windows.

## 0.120.1 — 10 November 2026

- Rebuilding a crystal (another number of cells, a surface, the hydrogen-bond network) no longer asks «Replace structure?» if the atoms were not edited.

## 0.120.0 — 10 November 2026

- A crystal tab now has its own panel: the buttons «Crystal», «View of the crystal» (along the axes, symmetry elements, ellipsoids, polyhedra), «Contacts» and «Powder pattern» above the model, and the arrow at the bottom sends the selected molecules to «Compass · Molecule» for a calculation. The buttons needed only by molecules (charges from a calculation, optimization constraints, the IUPAC name) are hidden for a crystal; editing the atoms stays.

## 0.119.0 — 10 November 2026

- A CIF now opens straight as a model of the crystal — without a window in between: one cell, whole molecules, the group and Z under the model. The window with the building settings, the surface, the contacts and the powder pattern is in «Edit → Crystal…».

## 0.118.1 — 10 November 2026

- The point group button of a crystal tab now names the crystal class — the point group of the crystal from its symmetry operations (for example, C2h = 2/m), as well as the space group and the crystal system, and not the symmetry of a random piece of the structure on the screen.

## 0.118.0 — 10 November 2026

- The «Crystal» window has an X-ray powder pattern with intensities: lines with hkl indices, a choice of radiation, an overlay of an experimental pattern from an .xy file. And a CIF that has only the symbol of the space group without the operations now opens correctly — the operations are taken from the tables of all 230 groups.

## 0.117.0 — 10 November 2026

- Inorganic crystals got coordination polyhedra: a box in the «Crystal» window outlines the metal atoms with the polyhedra of their nearest neighbours — rock salt shows Na octahedra, CsCl shows cubes. So the structure is read at once, without counting bonds.

## 0.116.0 — 10 November 2026

- The «Crystal» window has a number they like to ask in exams: the packing coefficient — what share of the cell the atoms take if counted as van der Waals balls. For molecular crystals it is usually from 0.65 to 0.77, for the closest packing of balls 0.74.

## 0.115.0 — 10 November 2026

- Experimental structures now look as in papers: the box «Displacement ellipsoids (50 %)» draws the thermal ellipsoids from the file around the atoms — stretched where the atom vibrates more.

## 0.114.0 — 10 November 2026

- Disordered crystals no longer look broken: if the file gives the atoms of part of a molecule in two positions, the box «One part of the disorder» places only one of them, not both on top of each other.

## 0.113.0 — 10 November 2026

- You can now take a piece of a crystal for a calculation: select an atom in each molecule you need — for example, in a pair bound by a hydrogen bond — and «Edit → Selected molecules — to a new molecule tab» carries them whole to «Compass · Molecule». From there — straight to Sextant.

## 0.112.0 — 10 November 2026

- The symmetry of a crystal can now be seen, not only read: the box «Symmetry elements» draws the axes, planes and inversion centres in the cell — screw axes and glide planes dashed, with symbols. And the buttons «Along a», «Along b», «Along c» and «Along the normal to (hkl)» set the crystal at once the way textbooks draw it.

## 0.111.0 — 10 November 2026

- A crystal now shows what holds its molecules together: the button «Contacts…» in the «Crystal» window lists the hydrogen bonds and short contacts between molecules with distances and angles, and «Show the hydrogen-bond network» lays out on the model the molecules of the cell together with the neighbours they are bound to.

## 0.110.0 — 10 November 2026

- A crystal in Compass now understands its symmetry: the window shows the space group, the system, the point group and the lattice type, Z, Z′ and the density, and every operation of the file is named in words — where a screw axis runs, where a glide plane lies. And the molecules are no longer cut by the faces of the cell: the box «Whole molecules» places each of them whole.

## 0.109.4 — 10 November 2026

- A little faster still: the program opens on the home page, and I start the Atlas — a whole built-in browser — a moment after the window has appeared. If you press «Atlas» at once, it opens without waiting.

## 0.109.3 — 10 November 2026

- A second try at a faster start — the first gained nothing: the models of the Atlas were prepared in parallel but still kept the window from being built. Now I take them up only when the window is already open, and the heaviest tables are computed by the first calculation that needs them.

## 0.109.2 — 10 November 2026

- The Azimuth window opens faster: it used to wait until the Atlas had prepared all its calculation models, though the first thing you see is the home page. Now the models are prepared aside, and everything is in place by the first calculation in the Atlas.

## 0.109.1 — 10 November 2026

- The side panel of the Atlas no longer shows the old name «Quantum chemistry Assistant & Solver» — it now says «Quantum chemistry · theory and calculation», as befits Azimuth.

## 0.109.0 — 10 November 2026

- Now I do not only say what went wrong in a calculation but offer a cure with one button: the SCF did not converge — «Repeat with hard SCF convergence»; the optimization ran out of cycles — «Continue from the last geometry»; there was not enough memory — fewer processes and more memory for each. Press it, and I set the settings myself and run the calculation again.

## 0.108.81 — 10 November 2026

- Menu items that cannot be pressed now (for example, populations without a result) are grey. Sextant has a «View» menu.

## 0.108.80 — 10 November 2026

- New menus: «Project» in Compass, «Server» in Sextant and «Help» in every section — with the manual, «What's new» and the installation check.

## 0.108.79 — 10 November 2026

- On Windows the items of drop-down lists no longer run over each other, and the menu of the method and the basis set closes with a second press.

## 0.108.78 — 10 November 2026

- «Install calculation programs…» now asks what to install, and the list has MOPAC. What the computer does not have yet is ticked.

## 0.108.77 — 10 November 2026

- On Windows two open Azimuths no longer get in each other's way in the Atlas: each takes its own port.

## 0.108.76 — 10 November 2026

- On Windows «Stop» now stops the whole calculation, not only ORCA itself — its parts no longer go on calculating. And the program finds xtb installed through conda by itself.

## 0.108.75 — 10 November 2026

- The program now has a license file: all rights reserved, to be used with the permission of the author. Until now that was said nowhere.

## 0.108.74 — 10 November 2026

- I took out the history of the calculations too: the list, its window, «Open the result», «Folder», «Clear the list». What is left in the part of the window that runs calculations is truly about the calculation itself.

## 0.108.73 — 10 November 2026

- My new helper for the programs asked itself for the path of the program, and the tests that put in a fake xtb could not fool it — it found the real one. Now it asks through the common door, as before.

## 0.108.72 — 10 November 2026

- And the third piece: the installation of the calculation programs — the question, the download from conda-forge, its progress in the calculation window. The part of the window that runs calculations went from 87 links down to 72, and each part taken out has its own short list of what it may touch.

## 0.108.71 — 10 November 2026

- I took out one more piece: everything that shows and chooses the program of the calculation — its mark, the tick, «Choose…», «Find it yourself», the line «not found». The part of the window that runs calculations now needs 74 things instead of 87.

## 0.108.70 — 10 November 2026

- I began to untangle the biggest part of the window — the one that runs calculations: it reached for 87 things of the window. Everything that watches the server — the mark «✓ free cores», the check of the connection, the files on the server — is now a part of its own that needs only nine.

## 0.108.69 — 10 November 2026

- When a queue on the server runs as one job, I now ask about it in one question: how the job is and which calculations have started and ended. If the server got a lot done while the program was closed, I no longer ask it once for every molecule.

## 0.108.68 — 10 November 2026

- By the second measurement choosing a molecule got almost twice as fast. I found one more small thing: at each choice I asked the database of the project fifty-eight times whether it had changed. Now I ask once.

## 0.108.67 — 10 November 2026

- Your measurement showed where the time goes when a molecule is chosen: I read every open tab of the project again, each one three times. Now I read once and remember, and I no longer parse the table of coordinates sixteen times in a row.

## 0.108.66 — 10 November 2026

- I measured your project of 44 molecules: most of the time went into reading the MOPAC results — I checked each of a thousand optimization steps for atoms stuck together. Now I check the first and the last — the biggest output is read in 0.8 s instead of 2.1. And to find the other delays in the window I learned to measure the project itself: run the measurement and I will see where it slows down.

## 0.108.65 — 10 November 2026

- I separated in a tab what it holds from how it is looked at: the history of undo, the pinned measurements, the open drawer of steps now live apart from the molecule and its settings — and a rule makes sure the view never gets into a project or an input file.

## 0.108.64 — 10 November 2026

- My new helper of the queue was given the whole of me, and the rules of the program do not allow that: each part gets only what it needs. Now it gets exactly the skills of mine it uses.

## 0.108.63 — 10 November 2026

- I took apart how a queue decides what to calculate next and moved it out of the window: the order — what runs on the server, what was sent, the next row, the search of a conformer, the end — is now checked without the window. Nothing changed for you, but it got harder to break.

## 0.108.62 — 10 November 2026

- If the connection breaks while I download a big file of orbitals, I no longer put the half of it into the folder of the calculation as if it were ready: I check its size against the server, download it again, and name honestly what never came whole.

## 0.108.61 — 10 November 2026

- If the server does not answer when you open the program, I no longer give up with an error: the project is open, and I say what I knew last — «running, last answer at 14:02» — and wait for the connection. A job gone from the queue? I do not rush to call it a failure but check three more times. And the same end of a calculation I record once.

## 0.108.60 — 10 November 2026

- I corrected myself: looking for drawn molecules at the exit, I closed the browsing of steps, and the program thought you had changed something — and asked about saving for nothing. It does not any more.

## 0.108.59 — 10 November 2026

- Drew a molecule on the empty tab and closed the program without saving? It is not lost: I put it as a draft into the «Projects» folder, and the home page keeps it for you marked «draft». And an XYZ whose frames are different molecules now opens as a project, like an SDF.

## 0.108.58 — 10 November 2026

- Changed the charge or the geometry of a molecule after its calculation? Now its name in the list gets «≠», and I tell you what changed. I leave the old result alone and never pass it off as a new one: it honestly stays the result of its own calculation until the new one is done.

## 0.108.57 — 10 November 2026

- The verification found a weak spot of mine: when a job ended and its row was no longer in the queue, I could write its result to the row running now. Not any more — a stranger's job stays nobody's, and the error log gets a note.

## 0.108.56 — 9 November 2026

- I tidied up the papers for developers: the version plan no longer waits for stage B, done long ago, the project contracts describe how an optimized geometry becomes the structure of the molecule by itself, and the architecture has a section on projects and calculations.

## 0.108.55 — 9 November 2026

- I reread my manual and gasped: forty new things had piled up in «How to view, select and measure». I put them where they belong — there are «Projects», «A queue on a server» and «Files on the server» now — dropped the notes about fixed bugs and corrected Sextant: the orbitals are in the additional settings, and a queue on a server is one job.

## 0.108.54 — 9 November 2026

- I fixed my test of a calculation on the server: a number of processes already in the field is not an edit by hand, and I rightly put the advice of the server there.

## 0.108.53 — 9 November 2026

- Right-click a molecule in the list of the project — «Calculation folder» opens the folder of its latest calculation.

## 0.108.52 — 9 November 2026

- The number of processes you set by hand with the server chosen is no longer replaced by my advice — even when the server answers later.

## 0.108.51 — 9 November 2026

- Chloride and iodide ions after MOPAC now open: I simply skip the asterisks MOPAC writes for a single atom.

## 0.108.50 — 9 November 2026

- An optimization converged, and the molecule of the project gets the optimized geometry by itself: the next calculation, ORCA after MOPAC for example, starts from it. The structure before stays in the history of attempts and in Undo.

## 0.108.49 — 9 November 2026

- While a queue computes the other molecules, the buttons «Atoms», «Bonds» and «Dipole» of Compass now work for a finished molecule of the project: charges, bond orders and the Multiwfn analyses are there at once.

## 0.108.48 — 9 November 2026

- I made the task setup panel wider and moved the choice of the starting orbitals of ORCA into «More settings» — now everything fits without scrolling.

## 0.108.47 — 9 November 2026

- Choose the server and I fill «Resources» with the cores and memory free there, as for your computer; I no longer ask before sending. And the settings of ORCA no longer run into each other: when they do not fit, the card scrolls.

## 0.108.46 — 9 November 2026

- In the batch mode the numbers of the molecules no longer vanish after the ninth: the column «No.» now holds both the tick and two or three digits.

## 0.108.45 — 9 November 2026

- On the home page under «Continue» and in «Recent files» a project is now labelled with its name — the one you gave it when saving — not the faceless project.qcc.

## 0.108.44 — 9 November 2026

- When I build a coordination centre, the charge and multiplicity now stay the ones I computed for the complex, not the ones guessed from the formula.

## 0.108.43 — 9 November 2026

- Molecules can be removed from a project: choose them in the list and press Delete or «Remove from project…» in the right-click menu; their calculation files too, if you wish.

## 0.108.42 — 9 November 2026

- ORCA is found on the server again even when the «Server…» setup lines were written for MOPAC; when the job of a queue cannot start on the server, the reason is shown.

## 0.108.41 — 9 November 2026

- While a queue runs, the blue band shows which molecule is being calculated instead of offering to start the queue again; the calculation window keeps its height from molecule to molecule; the result of each finished molecule appears in Compass (☰) and Spectrum right away.

## 0.108.40 — 9 November 2026

- «Edit → Geometry → Coordination centre…»: a metal and its ligands in an octahedron, tetrahedron, square plane or bipyramid in one step; the charge and multiplicity are set for you.

## 0.108.39 — 9 November 2026

- Sextant offers GAMESS (US) and NWChem: input files for energy, optimization, frequencies, transition state and TD-DFT (NWChem also NMR), run on this computer. A solvent and constraints are not written for them yet.

## 0.108.38 — 9 November 2026

- The model in the built-in renderer is drawn a little faster still.

## 0.108.37 — 9 November 2026

- Large molecules with atom labels are drawn much faster: the labels are no longer checked one by one against every atom. The theme switches faster too.

## 0.108.36 — 9 November 2026

- For development: the measurement script profiles drawing and the theme switch (`--profile`).

## 0.108.35 — 9 November 2026

- For development: a script of speed measurements, `tools/bench_workloads.py`.

## 0.108.34 — 9 November 2026

- The summary of a result in Spectrum and the checks of the reaction diagram and the Boltzmann shares now rest on the same facts of the output. A file still being written is not used as a key of saved analyses.

## 0.108.33 — 9 November 2026

- The queue of calculations is more reliable: the result of each calculation goes to its own row, even when another one runs by then, and only once.

## 0.108.32 — 9 November 2026

- An internal change: the end of a calculation (what came out, what goes to the history and the project, what to open) is now decided apart from the window and only once. Everything works as before; when the connection to the server was lost while sending, the calculation window now shows the message of the server as well.

## 0.108.31 — 9 November 2026

- Fixed a new test check: it read the installed libraries too.

## 0.108.30 — 9 November 2026

- When the connection was lost while a row of a queue was being sent and it is not known whether the server accepted it, the row now says so — «unknown whether the server accepted it», not «error». No repeat is prepared for it until the server is checked: the packages window has a «Check on the server» button. So one calculation is not sent to the server twice.

## 0.108.29 — 9 November 2026

- Fixed: since 0.108.28 the buttons of the calculation history window and «Skip», «QTAIM for all», «Descriptors» of the calculation window did nothing.

## 0.108.28 — 9 November 2026

- Running calculations, the input file and the queues of Sextant, and the «Tools» of Spectrum moved out of the main window. They work as before.

## 0.108.27 — 9 November 2026

- Fixed: since 0.108.25 orbitals, ESP and other surfaces did not open from the electron density window.

## 0.108.26 — 9 November 2026

- Four more parts of Compass moved out of the main window: the coordinates table, the model menus, the density panel and the calculation tools. They work as before.

## 0.108.25 — 9 November 2026

- Five more parts of Compass moved out of the main window: the surfaces and fields, the properties of a result, the opening of files, the «File» menu and the structure menus. They work as before.

## 0.108.24 — 9 November 2026

- Five more parts of Compass moved out of the main window: the steps of a calculation and the conformers, the overlay for comparison, the display schemes, the crystals and the view panel. They work as before.

## 0.108.23 — 9 November 2026

- The selection frame (Shift + drag) takes every atom inside it again, as before 0.108.21.

## 0.108.22 — 9 November 2026

- The blue ring around a selected atom no longer lies over the atoms in front of it: they hide it, as they hide the atom.

## 0.108.21 — 9 November 2026

- The selection frame (Shift + drag) no longer takes atoms hidden behind others — only those you can see. To take every atom inside the frame, hold Alt as well (Option on a Mac).

## 0.108.20 — 9 November 2026

- Five parts of Compass moved out of the main window at once: pictures and GIFs, IUPAC names and InChI, symmetry, selection and your own fragments. Each now lists beforehand what it needs from the window. They work as before.

## 0.108.19 — 9 November 2026

- The ribbons of a protein and the peptide builder moved out of the main window too. They work as before.

## 0.108.17 — 9 November 2026

- Three more parts of Compass moved out of the main window: opening the windows “Path between structures”, “Rotate about a bond” and “Conformer search”. They work as before.

## 0.108.16 — 9 November 2026

- An inner rebuilding: the optimization constraints (“the lock”) are the first part of Compass no longer sewn into the main window — it lives apart and knows of the window only what it needs. They work the same.

## 0.108.15 — 9 November 2026

- Inner order: the bookkeeping of the end of every row of a queue — the energy, why it failed, the record in the project — is now in the same separate part as for a single calculation, and is checked without the window. Nothing changed on the outside.

## 0.108.14 — 9 November 2026

- I now recognise surfaces, NCI and Multiwfn analyses by the content of the file, not by its name and time: if a file was replaced by another, even of the same size and date, the old picture is not shown. Next to an output of Multiwfn in “Анализ” lies a note of exactly which file it was made from.

## 0.108.13 — 9 November 2026

- If a calculation on the server failed, I now say what to do next: when the connection broke — check it in the history rather than run it again; when the server refused — check the login or the password. And the bookkeeping of the start and the end of a calculation is now a part of its own that can be checked without the window.

## 0.108.12 — 9 November 2026

- I now tell what is known of a result by codes, not only by sentences: “the optimization did not converge” and “the SCF did not converge” also reach the warnings of the reaction diagram and of the Boltzmann shares. And I sort failures into kinds — no connection, no data, damaged, not written — and know for each what may be done next.

## 0.108.11 — 9 November 2026

- Inner order: a test now checks that the scientific and service parts of the program do not depend on the window. It found one breach — the plot of the IR spectrum lay among the computing modules; I moved it.

## 0.108.10 — 9 November 2026

- If you switch “Where to compute” while a queue searches a conformer, the progress of the search no longer jumps into the window of the other place.

## 0.108.9 — 9 November 2026

- I handle the end of a calculation in the “slot” of the place where it ran — even if another place is chosen at that moment. Nothing changes on the outside; now it is guaranteed.

## 0.108.8 — 9 November 2026

- An inner rebuilding: the calculation on this computer and the one on a server are now kept as two separate objects, not as values whose meaning depends on the switch “Where to compute”. Nothing changed on the outside.

## 0.108.7 — 9 November 2026

- Saving a project became about a third faster: I write into the database only what changed, not the whole history of calculations again.

## 0.108.6 — 9 November 2026

- “Energies of several files” now warn the same way as the reaction diagram: if a calculation did not end normally, a structure has an imaginary frequency, or its charge is different or not known — it is written under the table of shares.

## 0.108.5 — 9 November 2026

- “Boltzmann shares” no longer drop a line with a typo in silence: I name the line I could not read. And nan or inf instead of an energy is now an error, not a table of nan.

## 0.108.4 — 9 November 2026

- If the database of a project is damaged or busy, I say plainly “the project database cannot be read” instead of taking the old copy of a file next to it — stale records of calculations are no longer passed off as real ones.

## 0.108.3 — 9 November 2026

- The queue of a project lives in its database too, and batch.json next to it stays as a copy for the list “Queues”. The conformers a queue found come to the tab of their molecule — even after a restart of the program.

## 0.108.2 — 9 November 2026

- The result of a calculation of a project molecule now always comes to its own tab — even if you moved to another molecule meanwhile or closed the tab of this one.

## 0.108.1 — 9 November 2026

- What a project knows of its calculations on the server — the job number, the sending, the link to the molecule, the ledger of analyses — is now in the database of the project too, not in separate files in the calculation folders. I read the old files of that kind and move them myself.

## 0.108.0 — 9 November 2026

- A project now keeps its molecules and its history of calculations in an SQLite database (project.sqlite): every change is written whole or not at all. I move an old project myself at its first save and keep its former file as project.qcc.v1-backup. Note: such a project opens only in Azimuth 0.108 or later — update the program of your colleagues.

## 0.107.7 — 8 November 2026

- If one project is opened in two Azimuth windows, only the first one writes to it — the second honestly says “read only”. “Save as…” gives the copy of a project its own identifier.

## 0.107.6 — 8 November 2026

- QTAIM of a queue now works on a copy of the orbital file taken when the analysis starts: if you recalculate a molecule while the analysis runs, the result stays honest. I record every analysis in “Анализ/analyses.json”, and a Multiwfn error no longer looks like a failed calculation.

## 0.107.5 — 8 November 2026

- A queue sent to the server as one job is no longer doubled when the connection breaks either: I check with the server instead of sending the same calculations one by one. Every calculation of the queue on the server now marks which attempt it belongs to.

## 0.107.4 — 8 November 2026

- If the connection to the server breaks exactly while a calculation is being queued, I no longer say “error” and no longer queue a second copy. I ask the server whether it accepted the job and keep watching it. If the server does not answer, the calculation history shows “not known whether the server accepted it — check”.

## 0.107.3 — 8 November 2026

- The queue of a project and choosing a molecule in the list take the molecules with their latest edits, even those not saved yet.

## 0.107.2 — 8 November 2026

- A new project now lives at once in “Documents/Azimuth/Проекты” under its own name. “Save” only confirms the name, and no second copy of the project appears any more.

## 0.107.1 — 8 November 2026

- Each project now has one keeper of its molecules — the session. Saving, export and adding molecules take the data from it instead of guessing by the tab on screen.

## 0.107.0 — 8 November 2026

- I have begun a big rebuilding of projects and calculations. So far it is the foundation: I wrote down who owns what and which states a calculation can be in — «connection lost» no longer means «error».

## 0.106.18 — 8 November 2026

- Ethanol and dimethyl ether share one formula but are different substances. Now I rank a queue as conformers only when you started it from the page «Conformers».

## 0.106.17 — 8 November 2026

- I found why one molecule of your set was left without hydrogens: in the flat drawing the two hydrogens of a ring fusion ran into each other. Now I put them above the plane, as wedges.

## 0.106.16 — 8 November 2026

- In «Files on the server» several files can now be selected at once, and all the selected ones are deleted, not just the last one. And in a long queue I really keep the molecule being counted now in sight.

## 0.106.15 — 8 November 2026

- A flat drawing of a cage with straight chains — a cryptand, for example — is no longer left without hydrogens: I add them even where the bonds of an atom point exactly at each other.

## 0.106.14 — 8 November 2026

- I no longer pass different molecules of a project off as conformers: after a queue «Go to Compass» opens the project and the list of its molecules, and «Conformers» stays for the structures of one substance.

## 0.106.13 — 8 November 2026

- If you closed the program in the middle of a queue, after the start I not only watch the server again but also open the project of that queue in Compass — the molecules are there and the results go into them.

## 0.106.12 — 8 November 2026

- The list of a queue now fits in my card: it takes the room that is left and scrolls the rest. And the molecule I am counting now I always keep in sight.

## 0.106.11 — 8 November 2026

- While a queue runs and you are in Compass or Spectrum, I no longer pop up after every molecule. I quietly go on counting, and the hourglass shows how things stand.

## 0.106.10 — 8 November 2026

- I dressed the «Files on the server» window in our style: two white cards, the chosen one framed in blue, folders and files with their own glyphs, and the keys F3–F8 written at the bottom.

## 0.106.9 — 8 November 2026

- A queue now goes to the server as one parcel: I pack all the calculations into an archive and send it at once instead of calling the server twice for every calculation.

## 0.106.8 — 8 November 2026

- Drop a file on the window and you can swipe away to other apps at once while I make the molecules three-dimensional. Before, macOS thought you were still dragging the file and waited for me.

## 0.106.7 — 8 November 2026

- Now you can look into the server right from Sextant: two panes — your computer and the server. Copy, open results, edit inputs, delete what is not needed.

## 0.106.6 — 8 November 2026

- I now send a server queue whole: the server runs the calculations one after another by itself, and I only keep an eye on them. Close the program without worry — at the exit I have nothing left to send.

## 0.106.5 — 8 November 2026

- Bring a file over the window and I turn grey and tell you what can be dropped here: structures into Compass, input files into Sextant, results into Spectrum.

## 0.106.4 — 8 November 2026

- Write me a sequence — AEAAAKEAAAKA, say — and I assemble the peptide: as a helix, a β-strand or an extended chain, of L-amino acids, with side chains that do not push each other.

## 0.106.3 — 8 November 2026

- Open a protein from the PDB and turn on «View → Protein ribbon»: I find the chain, the helices and the β-strands myself and draw them as bands and arrows, as in a biochemistry textbook.

## 0.106.2 — 8 November 2026

- A scan can now be two-dimensional: ORCA walks a grid of two coordinates, and I draw the energy as a map with isolines — like a map of mountains. Click a point on the map and I show the molecule there.

## 0.106.1 — 8 November 2026

- Now I compute with ORCA not only the NMR shifts but the J couplings too — and draw how a signal splits: the quartet of the CH₂ of ethanol, the triplet of the CH₃, the doublets of doublets of vinyl protons. Choose a signal in the table and I show its multiplet in hertz.

## 0.106.0 — 8 November 2026

- I have learnt a real force field — UFF. Ask for «Optimize (UFF)» and I show the energy of the molecule in kcal/mol and what it is made of: bonds, angles, twists, the pushing of atoms. With «Tidy with UFF» new atoms settle by it too.

## 0.105.19 — 8 November 2026

- You can now ask me to compute a molecule with xtb right from Compass — the energy, an optimization, frequencies or a scan of the selected atoms. And I save the steps of any calculation as one file, draw how a length or an angle changes along them, and tell you in which vibrations the chosen atoms take part.

## 0.105.17 — 8 November 2026

- Compass and Spectrum are now sorted into folders: window parts, chemistry, the model field and panels for Compass; output readers, Multiwfn, analyses and windows for Spectrum.

## 0.105.16 — 8 November 2026

- I took away a dozen «look over there» signposts inside the program: now every part of it knows at once where what it needs lives.

## 0.105.15 — 8 November 2026

- I sorted the documents of the program into folders: setup, features, plans, drawings, checks and the archive.

## 0.105.14 — 8 November 2026

- I took a few files the program never used out of its folder — my old quiz poses among them. They are not lost: they can be brought back from the history.

## 0.105.13 — 8 November 2026

- The «Project history and files» window is simpler: only the history of calculations and adding files, and it no longer pops up by itself.

## 0.105.12 — 8 November 2026

- The window opens a little faster: I no longer prepare every translation pattern in advance, only the ones that actually come up.

## 0.105.11 — 8 November 2026

- More sorting onto shelves: Compass, its field with the molecule and the window with the sections are now made of smaller parts. Everything works as before.

## 0.105.10 — 8 November 2026

- I sorted Sextant onto shelves: running calculations and input files now live in parts of their own. Nothing changes on the outside.

## 0.105.9 — 8 November 2026

- When the Atlas window closes while a page is still loading, no scary error shows up in the console any more — it was only a cut-off reply.

## 0.105.8 — 8 November 2026

- The last part of the big tidy-up: the hidden rows of the old tabs are gone from Compass, Sextant and Spectrum — the tabs are now those of projects only.

## 0.105.7 — 8 November 2026

- The list of molecules of a project no longer jumps to the top when you pick a molecule or tick a box.

## 0.105.6 — 8 November 2026

- While a calculation runs I read only the new lines of its output, not the whole file every second — and the optimization cycles are now counted correctly even in a very long output.

## 0.105.5 — 8 November 2026

- The project file is no longer rewritten on every click in the list — only when something in the project has changed.

## 0.105.4 — 8 November 2026

- Some housekeeping inside: the hidden buttons and lists the menus rely on now live inside the window and go away with it.

## 0.105.3 — 8 November 2026

- A molecule from SMILES is now built many times faster — usually in a fraction of a second, and the geometry is no worse than before.

## 0.105.2 — 8 November 2026

- A queue in another jobs folder no longer trips over the project, and English and Chinese labels no longer get mixed up.

## 0.105.1 — 8 November 2026

- A little more tidying: the old «Structures» page of the left panel is gone for good — a set of structures is simply the molecules of your project.

## 0.105.0 — 8 November 2026

- I tidied up: any file of structures now opens one way — as a project. The residues of a PDB are shown as atom labels again.

## 0.104.9 — 8 November 2026

- A project is no longer re-read whole at every click in the list — choosing a molecule and switching the mode should be noticeably faster on large sets.

## 0.104.8 — 8 November 2026

- In Spectrum the tabs now sit on the left, right on top of the panels as in Compass; the tables fill their cards, and every tab has a neat frame.

## 0.104.7 — 8 November 2026

- In Spectrum the result tabs are now inside the panel, and it stands level with the list of molecules — as in Compass and Sextant.

## 0.104.6 — 8 November 2026

- The list of molecules has a switch «Single | Batch». In the batch mode every molecule is ticked — untick one and I skip it; the ticked ones are calculated and analysed. And I removed the extra buttons under the list.

## 0.104.5 — 8 November 2026

- Trajectories (XYZ with frames, PDB with MODEL) open as steps again, «Recent files» lists your files rather than drafts, and Ctrl+Z after added hydrogens works in a project too.

## 0.104.4 — 8 November 2026

- Panels now slide evenly: the model beside them no longer shivers while they move.

## 0.104.3 — 8 November 2026

- The list of molecules is now a neat card with rounded corners, like the other panels. And the turn buttons on the right fold away by their chevron when they are in the way — and come back.

## 0.104.2 — 8 November 2026

- The list of molecules now slides out smoothly, like the result panel, and slides back just as smoothly.

## 0.104.1 — 8 November 2026

- The list of the molecules of a project now looks like the old «Structures» page: number, name and formula in a neat table, the buttons below it. The separate «Structures» page is no longer needed.

## 0.104.0 — 7 November 2026

- A tab is now a whole project: on the left there is one list of its molecules, the same in Compass, Sextant and Spectrum. Pick a molecule and I show its structure, settings or result right where you are.

## 0.103.0 — 7 November 2026

- Settings now have a switch «search the best conformer before a queue» and a choice of method — from quick RDKit to CREST. Turn it on and I first find the lowest conformer before each calculation.

## 0.102.0 — 7 November 2026

- For a set of ligands you can switch on «Complexes with an ion»: I put the ion (Cs⁺, Sr²⁺ …) into each ligand myself, compute the ion, the ligands and the complexes, and give the binding energies at the end — with the BSSE correction if you like.

## 0.101.0 — 7 November 2026

- After a queue you can open «Descriptors and logK»: each molecule sits next to its SDF constants, energies, metal surroundings, charges and QTAIM. Pick what to compare — I draw the line and tell you R², Q² and who stands out.

## 0.100.2 — 7 November 2026

- While I wait, a thin ring turns at the left of the message, and the message no longer hides under the panel. In Sextant a long queue scrolls and shows how many molecules are left. And when the group comes out C1, I tell you which symmetry the structure is close to.

## 0.100.1 — 7 November 2026

- The structure list on the left no longer needs «Take this structure»: the one you choose stays when you close the panel. The panel slides more smoothly and the model no longer twitches.

## 0.100.0 — 7 November 2026

- You can now keep a project: one folder with all your molecules, their source files and every calculation attempt. A failed retry never replaces a good result, and the whole folder can be moved to another computer.

## 0.99.1 — 7 November 2026

- While I wait it now shows: a sign turns in the pill over the model, the time runs and it says how many structures are done.

## 0.99.0 — 7 November 2026

- While I compute or load something, no «Please wait» window pops up any more: the cursor just turns into a spinning circle, and the bottom line says what is going on and how much is done. Changed your mind — press Esc.

## 0.98.2 — 7 November 2026

- A 3D file whose carbons just happen to lie in one plane (like the butane of the examples) is no longer taken for a flat drawing.

## 0.98.1 — 7 November 2026

- When a structure of a file is flat, I now ask myself whether to make it three-dimensional — one button and it is done. I do not ask about molecules that really are flat, like benzene or nitrate.

## 0.98.0 — 7 November 2026

- When a file has flat 2D structures I now say so at once, and «Geometry → Make 3D (RDKit)…» makes them three-dimensional, keeping their charges and names. For macrocycles a conformer search is the next step.

## 0.97.2 — 7 November 2026

- When a MOL or SDF file writes the charges of its atoms, I now read them: chloride stays Cl⁻, nitrate NO₃⁻ without extra hydrogens, and they go to a queue with their own charge.

## 0.97.1 — 7 November 2026

- If the connection to the server is lost for a minute, I wait and try again instead of marking a finished calculation as failed. That is how four molecules of your queue were lost.

## 0.97.0 — 7 November 2026

- In the window of packages you can choose the rows that failed, see what went wrong, fix the structure, the charge or the spin and make a new package of them. The old package stays as it was, and the new one starts only at your button.

## 0.96.1 — 7 November 2026

- A finished package of calculations now opens whole — «Calculation → Calculation packages…»: every row, its state and result. The finished structures go to Compass at one click, with their charges and multiplicities.

## 0.96.0 — 7 November 2026

- A queue on a server now runs without me: when you quit I send every remaining calculation there — they run one after another. At the next start I take the queue up, collect what is done and watch the rest, sending nothing again and not asking about the cores again.

## 0.95.0 — 7 November 2026

- If you close Azimuth while a calculation runs on a server, at the next start I ask whether to check it. And if a queue was running, I open the whole of it, with the calculations done and waiting — the one that ran on the server is not sent again, I go on watching it.

## 0.94.0 — 7 November 2026

- After a queue of calculations I can find the critical points of all the molecules at once: the button «QTAIM for all» in the window of the queue. Three tables appear in the folder of the queue — a summary of the molecules, all the bond points and all the weak interactions.

## 0.93.0 — 7 November 2026

- If Azimuth closes in a crash, the molecule tabs are not lost: every half minute I put a copy of them aside, and at the next start I offer to restore them — in new tabs, without touching your files. And «Save» before quitting now saves every changed tab, not only the open one.

## 0.92.2 — 7 November 2026

- CREST 2.12 did not start on a Mac after installing — it could not find its library. I now put it into the folder of the programs as a file of its own and check at once that it starts.

## 0.92.1 — 7 November 2026

- On a Mac I now install CREST 2.12: version 3.0.2 has a broken sorting there — the energy window is always zero, and any search left one conformer. If such a CREST is already installed, I say so and tell you how to reinstall it.

## 0.92.0 — 7 November 2026

- After the critical points are found I now name every interaction: a hydrogen, halogen, chalcogen, pnictogen or tetrel bond, or a van der Waals contact. I decide by the geometry — where an atom points and how close it is — and the bond point confirms it. For a hydrogen bond with a point I estimate its energy from ρ; bonds without a point are listed under the table.

## 0.91.83 — 7 November 2026

- I now write an excited-state optimization with B3LYP as LibXC(B3LYP): ORCA 6.1 stopped at once without it. It is the same functional — the energy agrees with the old one to a millionth of a hartree.

## 0.91.82 — 7 November 2026

- Yttrium, silver, iodine and the other elements from rubidium to barium now also get the relativistic SARC basis with DKH and ZORA — I thought ORCA had none for them, but it does.

## 0.91.81 — 7 November 2026

- I no longer say «the optimization did not converge» after an ORCA optimization that did: I took the intermediate cycles for the last one. And if ORCA 6.1 refuses an excited-state optimization with B3LYP, I tell you what to change in the input.

## 0.91.80 — 5 November 2026

- I put the new tools where they belong: in Compass — a table of every length and angle, the volume of the molecule and a comparison with the next tab; in Spectrum — the isotope pattern, the energies of several calculations at once and the Boltzmann shares.

## 0.91.79 — 5 November 2026

- Instead of a dozen ready looks — your own: the size of atoms, the width of bonds, the background, the colour of every element, all in one window and on the model at once. Like it — keep it under your own name and share the file.

## 0.91.78 — 5 November 2026

- «View» grew more flexible: the molecule can turn about any atom, atoms in the way can be hidden, the camera set by numbers and a view repeated, bonds labelled with their orders and atoms wrapped in van der Waals clouds.

## 0.91.77 — 5 November 2026

- I now draw arrows and planes on the model: through a ring, along a normal, from atom to atom — and measure the angles between them. Handy for seeing how two rings lie over each other.

## 0.91.76 — 5 November 2026

- «Edit» grew: atoms can now be renumbered by clicks — the first one selected becomes number one — turned and moved by an exact angle and vector, and I can measure the planes of rings and the angle between them.

## 0.91.75 — 5 November 2026

- The «File» menu grew: Ctrl+S no longer asks for the name again, Ctrl+W closes a tab, «Clear» sweeps everything down to a blank sheet, and a molecule can now be called by its name — I fetch it from PubChem — or simply pasted from the clipboard.

## 0.91.74 — 5 November 2026

- I tidied up the checks: one of them forgot to clean up after itself, and the next one fell over. Nothing changed on the outside.

## 0.91.73 — 5 November 2026

- Four more sections of «Settings»: energies in kcal, kJ or eV, the scheme I wake up with, quick drawing of large molecules and the paths to all six programs. And all the settings can now go into a file and on to another computer.

## 0.91.72 — 5 November 2026

- In «Settings» you can now decide how generously I join atoms with bonds, whether the optimization steps keep one orientation (no more jumping) and what pictures and spectra look like by default. I drew an icon for every section, and «Defaults» brings everything back.

## 0.91.71 — 5 November 2026

- CO, CO₂, N₂ and other molecules without hydrogens now open from a file as they are. Hydrogens are added only when the molecule has a C–C bond.

## 0.91.70 — 5 November 2026

- “File → Open calculation result…” opens a file again. Before, the output window of Sextant appeared instead.

## 0.91.69 — 5 November 2026

- The File menu has “Recent files” and “Reload file” (Ctrl+R). Reloading is handy while a calculation is still running: the output is read again in the same tab.
- “Save several files” saves all the structures of a set at once: as one XYZ or SDF, each in its own file, or as pictures.

## 0.91.68 — 5 November 2026

- The menus have icons now too: File, Edit, View and the right-click menus of the model. That is 31 more new icons.

## 0.91.67 — 5 November 2026

- The buttons with words now have icons in the same thin style as the toolbars: “Save picture…” with a picture, “Build map” with a map, “Take this geometry” with an arrow going in. There are 45 new icons.

## 0.91.66 — 5 November 2026

- If a calculation has already gone to the server and something fails to save on this computer (a full disk, say), Sextant no longer stops watching it: it tells you the job number and follows the calculation to the end.
- Big CUBE and orbital files are read without freezing the window, and opening the same file again and again no longer loads the processor with needless work.

## 0.91.65 — 4 November 2026

- A molecule from SMILES or from a name is built and tidied about one and a half times faster — the same geometry.

## 0.91.64 — 4 November 2026

- Sextant’s advice now knows the heavy elements. It treats Pt and Pd as metals. For the lanthanides it turns on DKH2 itself, so they get the SARC basis. And for the atoms with a pseudopotential, it says so.
- The advanced settings have “Basis sets by element”: for example def2-TZVP on iron and def2-SVP on the other atoms; the button “Add…” offers the elements of the molecule.

## 0.91.63 — 4 November 2026

- Sextant is no longer limited to the elements up to krypton. With def2 the heavy atoms up to radon get their pseudopotential — Y, Ag, I, Pt, Au, Bi. With DKH and ZORA in ORCA the lanthanides, the 5d metals and the actinides get the all-electron SARC basis, and with X2C the x2c basis sets up to radon. When an atom has no suitable basis, Sextant says plainly what to choose instead.

## 0.91.62 — 4 November 2026

- Installing on Windows no longer stops at the last check, and installs Python 3.13 by itself when there is none.
- With DKH, ZORA and X2C, Sextant now writes the matching relativistic basis set for ORCA (DKH-def2-TZVP, ZORA-def2-TZVP, x2c-TZVPall) — as the Atlas topic “Heavy elements” teaches.
- The new Atlas topics fit a phone screen.

## 0.91.55 — 3 November 2026

- On Windows xtb, MOPAC and MS-MPI for ORCA are now installed with one button in Sextant — no administrator rights, no hunting around websites.

## 0.91.54 — 3 November 2026

- Change the grid and the surface on the model is drawn again on the new one: a rough look first, then a precise one.

## 0.91.53 — 3 November 2026

- The screen no longer turns black when you switch sections on Windows. Spectra and maps have frames now, and the map and the profile in Spectrum stand side by side.

## 0.91.52 — 3 November 2026

- The buttons above the Compass model open at the first press and close at the second, the icons are sharp at any screen scale, and in the dark theme the buttons are now the same blue as the language switch.

## 0.91.51 — 3 November 2026

- No more black windows flashing on Windows: ORCA, Multiwfn and the other programs work quietly in the background, and you follow the calculation in the Sextant window.

## 0.91.49 — 3 November 2026

- On Windows a stray blue line showed up in my greeting — erased it. And signing in to a server with a password no longer minds a Cyrillic user name.

## 0.91.48 — 3 November 2026

- On Windows Multiwfn quietly waited for someone to press Enter and mixed up all the answers. Now we have an agreement: charges, orbitals and excitation analyses work there too.

## 0.91.46 — 3 November 2026

- For the first time I went through all the checks on Windows: fixed a list that stuck out of the window of the Sextant settings and a couple of small things you never see on a Mac.

## 0.91.45 — 3 November 2026

- I tidied up before the beta: cleared out what the code no longer used and drew up an index of every module — now it is plain where everything lives. Nothing changed on the outside, and that was the point.

## 0.91.44 — 3 November 2026

- If something breaks, I will not stay silent any more: I write the error down, tell you about it and help you put together a report for the author — one file, no passwords.

## 0.91.43 — 3 November 2026

### Compass

- The charges are on their shelves: charges, spins, Fukui — each in its own submenu. And the eraser next to them takes everything extra off the molecule in one click, surfaces too.

## 0.91.42 — 3 November 2026

### Spectrum

- Fewer tabs in sight: «Result», «Spectra» and «Wavefunction», each with its own inside. And a folder: every analysis table lies in «Analysis», and now an icon takes you there.

## 0.91.41 — 3 November 2026

- Atoms now have proper names: not «3» but «C3». In the maps, the fragments and the selection by numbers you can type either way — and if a number does not match its element, I will tell you.

## 0.91.40 — 3 November 2026

### Sextant and Compass

- A new task «CDA»: the complex and its two fragments at one geometry — and you see how many electrons the ligand gave to the metal and how many it got back. A fragment can simply be selected in Compass.

## 0.91.39 — 2 November 2026

### Sextant

- MOPAC learned to travel to the server: a single calculation and a queue alike. I ask how many threads to give it, so that it does not take the whole server.

## 0.91.38 — 2 November 2026

### Compass

- The Fukui functions are no longer just numbers at the atoms but clouds on the model: f⁺, f⁻, f⁰ and Δf — you see where an electron comes and where it leaves from.

## 0.91.37 — 2 November 2026

### Compass

- The surfaces in the result panel grow as a tree: branches for the density, localization, energy, potential, weak interactions; fold what you do not need.
- The density difference Δρ explains itself in three steps, and the fragment buttons became icons that no longer get cut off.

## 0.91.36 — 2 November 2026

### Compass

- The «±» button above the model split into three: «Atoms» — charges and spins, «Bonds» — bond orders, «Dipole and forces» — the arrows. The menus got shorter, and what you need got closer.

## 0.91.35 — 2 November 2026

### The whole program

- «File → Settings…» and a gear in the left panel: language, theme, hydrogens, the calculations folder, Multiwfn — and at last the separator of the CSV tables, apart from the decimal sign. All in one window, not in the corners of the menus.
- The hourglass no longer hides under the magnifier of the Atlas.

### Compass and Sextant

- An SDF database no longer calls every molecule «Molfile»: the name comes from the `<Name>` item of the record, and the calculation queue shows at once who is being calculated.
- An interrupted calculation no longer leaves a heap of .tmp behind — I sweep up after ORCA and Gaussian after an error, after a stop, and on the server too.

## 0.91.34 — 2 November 2026

### Sextant and Compass

- A new task «Fukui functions»: three calculations — the molecule, its anion and its cation — and the model shows where a nucleophile, an electrophile and a radical attack; the window also gives the ionization potential, the electron affinity, the hardness and the electrophilicity.

## 0.91.33 — 2 November 2026

### Compass

- «±» has «RESP charges…»: charges fitted to the electrostatic potential, as in the AMBER and GAFF force fields, and a file with them for molecular dynamics.

## 0.91.31 — 2 November 2026

### Spectrum

- The UV-Vis tab has «Charge transfer…»: how much of the electron of an excited state moves from one part of the molecule to another (the fragments by atom numbers or by the Compass selection), and the heat map of the transition matrix by fragments and by atoms.

## 0.91.30 — 2 November 2026

### Compass

- Localized orbitals now work for open-shell radicals and ions too — separately for α and β.

## 0.91.29 — 2 November 2026

### Compass

- In the «Orbitals» panel you can switch to localized orbitals: instead of the canonical ones spread over the molecule I show the cores, the lone pairs and the bonds — the way chemists draw them — and say which atoms they are on. The chosen orbital goes onto the model.

## 0.91.28 — 2 November 2026

### Compass

- For an open shell «Hirshfeld charges…» now also shows the spin on every atom — for Gaussian and Molden files too, not only for ORCA.

## 0.91.27 — 2 November 2026

### Compass

- The «±» menu now has the charges of Bader's atoms in molecules: I divide the molecule into the basins of the electron density and count the electrons in each. For an open shell I also show the spin of every basin. For Gaussian and Molden files I compute the Hirshfeld charges too — before, only ORCA had them.

## 0.91.25 — 2 November 2026

### Spectrum

- A new tab «Delocalization»: how many electron pairs atoms share — for a complex you see whether the metal–ligand bond is covalent or ionic — and how aromatic the rings are. HOMA I compute at once from the bond lengths, FLU, PDI and MCI together with Multiwfn.

## 0.91.24 — 2 November 2026

### Spectrum

- A new tab «Density of states»: I spread the orbitals over energy and show how much of each element is in them — for a complex you see at once where the d orbitals of the metal are, where the ligands are, and the HOMO–LUMO gap. You can select atoms in Compass and see their share separately, and OPDOS shows whether the orbitals between two fragments are bonding or antibonding.

## 0.91.23 — 2 November 2026

### Spectrum

- «Vibrations and IR» and «Thermochemistry» are now laid out in cards with titles — like «Energies and frequencies»: the spectrum, the modes and the vibration itself, the energies and the entropy.

## 0.91.22 — 2 November 2026

### Sextant and Spectrum

- Excited states can now be looked at through natural transition orbitals. Tick «NTO» for the UV-Vis spectrum in Sextant (ORCA), and in Spectrum under the table of states I show where the electron leaves from and where it goes — usually one pair of orbitals almost entirely. The compass icon next to it puts that orbital on the model.

## 0.91.21 — 2 November 2026

### Sextant

- An ORCA calculation can now start from the orbitals of an earlier one: there is «Orbitals» under the task — choose a .gbw file and the SCF starts from it. It helps after a broken calculation, or when you change the method or the geometry a little — it converges faster and to the same state.

## 0.91.20 — 2 November 2026

### Sextant

- A new task — «Relaxed PES scan». Mark a length, an angle or a dihedral in Compass as an optimization constraint, and in Sextant I show its current value and ask how far to take it and in how many points. At every point the rest of the molecule is optimized, and then all the points appear in the ☰ panel of Compass with an energy plot. For ORCA and Gaussian so far.

## 0.91.19 — 2 November 2026

### Sextant

- If you calculated with MOPAC or xtb last time, at the next start I no longer scare you with «The method, basis set or task is not supported» — the input file is ready at once.

## 0.91.18 — 2 November 2026

### Sextant and the home page

- If a calculation breaks off with an error, I now put the steps it managed to make into its tab myself: the last geometry is already on the model, and «Go to Compass» opens the steps — you can start again from it at once. And on the home page I no longer block the azimuth dial with a whole rectangle: only my desk and I cover it. «Calculation history» has a «Clear the list» button now, and the note under «Frequencies and thermochemistry» is no longer cut off.

## 0.91.17 — 2 November 2026

### Compass and Spectrum

- You can now go between Compass and Spectrum by icons: the panel left of the model has the spectrum icon on every page, and Spectrum has the compass icon wherever something can be shown on the model. I numbered the critical points by kind — n1, b1, r1, c1 — and wrote the numbers on the molecule itself, so a row of the table is easy to find by eye. And in «Density topology» a single click no longer carries you off to Compass: a double click does.

## 0.91.16 — 2 November 2026

### Sextant and Spectrum

- Now when you choose a task I set a fitting method and basis set myself — CAM-B3LYP for a UV-Vis spectrum, for example — and say so below; you can change them as usual. There are SMD for the solvent, D3(0) among the dispersions and a check of the stability of the wavefunction. And the molecules of databases without names I name by their formula.

## 0.91.15 — 2 November 2026

### Sextant and Spectrum

- Sextant has two new tasks: «Frequencies and thermochemistry» at a ready geometry and «Transition state + frequencies». If you choose a functional with which ORCA cannot optimize an excited state, I tell you at once and suggest one that works. In Spectrum the result now sits on one panel, and the tables are neat. And the molecule no longer blurs while you turn it.

## 0.91.14 — 2 November 2026

### Sextant and Spectrum

- In Sextant I now offer each program only what it can do: you will not see spectra in MOPAC or NMR in Psi4. The settings of the chosen task — the temperature for frequencies, the number of states for TD-DFT — are right under the fields instead of hiding in the additional settings. In Spectrum I lined up the tabs and put the file name in one row with the buttons.

## 0.91.12 — 2 November 2026

### All sections

- I went through every window and menu and gave them one look: the text fields are rounded and easy to see in the dark theme, check boxes have their boxes, long items of drop-down lists are no longer cut, and in my messages the main point is in bold and the details in the plain font.

## 0.91.11 — 2 November 2026

### Compass

- When I add hydrogens, I follow the double bonds written in the file: C=C and C=O get fewer hydrogens whatever the bond length. I now read pyrrole without hydrogens correctly — the hydrogen goes on the nitrogen, not an extra one on a carbon.

## 0.91.10 — 2 November 2026

### Compass

- If a file has the heavy atoms only — as databases often do — I add the hydrogens by the valences right away and say how many. If you don’t want them, Ctrl+Z gives the file back, and «File → Add hydrogens to files without H» turns it off. I complete SDF sets as a whole too, so they can go straight into a Sextant queue.

## 0.91.8 — 2 November 2026

### Sextant

- When you choose conformers for a queue, I now show it: a blue band «Queue: …» in the calculation card and the button «Run the queue». Before it starts you can still change the settings, or go back to one calculation with the cross.
- The queue is not only for ORCA: you can run all the conformers through MOPAC — I sort them by the heat of formation.

## 0.91.7 — 2 November 2026

### Sextant

- I now run conformers as a queue: after a search, press «Calculation queue for the set…» at the input file — I check those within 3 kcal/mol of the lowest (you can choose how many) and compute them one at a time with the same settings, here or on the server. At the end I sort them again by the new energies on the «Conformers» page in Compass and write a table with the Boltzmann shares. If the program was closed in the middle of a queue, «Resume the queue» finishes it.

## 0.91.6 — 2 November 2026

### Spectrum

- I now show MOPAC orbitals: when an `.aux` lies next to the output, press «Orbitals…» — as for other programs. And in the «Thermochemistry» tab I compute the MOPAC heat of formation at any temperature and check myself against the table MOPAC printed.

## 0.91.5 — 2 November 2026

### Sextant

- You can now compute in MOPAC: choose it in the list of programs, the method — PM7 or another semiempirical one, and in seconds you will have a result even for a big molecule. I write «Optimization + frequencies» into one file: first MOPAC optimizes, then it computes the frequencies at the same geometry. And if MOPAC, xtb or CREST is not installed yet, I will install it into the program folder myself.

## 0.91.4 — 2 November 2026

### Spectrum and Compass

- If you chose circular dichroism, I no longer go back to absorption when you open the next result. And the overlay of two structures is more reliable for small flat molecules whose coordinates are a little «noisy».

## 0.91.3 — 2 November 2026

### Compass

- While the bees look for conformers, I say where they are: the global search or which local search it is — and at most how many there will be. So you can see how much longer to wait.

## 0.91.2 — 2 November 2026

### Compass

- I remade the conformer search window. The method is now chosen in a list, and I show only its settings — and I suggest a suitable one at once: the scan for a molecule with a couple of rotatable bonds, the bees for a flexible one, CREST for a really big one. The scan refines its candidates in xtb by itself, and I ask CREST to search twice as long for small molecules.

## 0.91.1 — 1 November 2026

### Compass

- You asked why I always find one conformer. I did find them, but hid them: I threw away everything more than 6 kcal/mol above the lowest, and the bees everything more than 1.7 above. Now the energy window can be widened, the bees obey the same window, and I tell you how many structures stayed outside it. For instance, anti formic acid is 7.1 kcal/mol above syn — widen the window to 8 and you will see it.

## 0.91.0 — 1 November 2026

### Spectrum

- I now read MOPAC. Open its output and I will show the heat of formation, the optimization steps, the charges and the vibrations. Just remember: MOPAC gives a heat of formation, not a total energy, so compare it only with other MOPAC calculations of the same method. And one more thing: MOPAC computes frequencies wherever you left it, even if the molecule is not optimized — I will warn you if that happened.

## 0.90.1 — 1 November 2026

### Spectrum

- I now show Raman scattering spectra. Tick «Raman» in Sextant — ORCA computes the activities, and on the «Vibrations and IR» tab you can switch from IR to Raman. The table gives the depolarization ratio: if it is 0.75, the vibration is not totally symmetric. And with ethylene you will see the rule of mutual exclusion — what is seen in IR is absent in Raman, and the other way round.

## 0.90.0 — 1 November 2026

### Spectrum

- I now show electronic circular dichroism. When ORCA or Gaussian computed rotatory strengths, choose «Circular dichroism (ECD)» on the UV-Vis tab: the bands go up or down by the sign of the rotatory strength, and the mirror-image isomer has everything reversed. With such a spectrum and an experiment you can tell whether you have R or S. If the molecule is achiral, I will say so — it has no ECD.

## 0.89.28 — 1 November 2026

### Windows

- Getting ready for Windows: I now read the replies of other programs and files as UTF-8 everywhere. On Windows with the Russian locale a single unknown character in a program's reply could stop the reading altogether; now it becomes «�» and I read the rest.

## 0.89.27 — 1 November 2026

### Spectrum

- I checked Gaussian 09 TD-DFT on your calculation with 40 states. I found a mistake: for excited-state optimizations and frequencies I took the ground-state energy, and the free energy came out 0.17 hartree wrong. Now the energy is that of the state Gaussian follows, and the thermochemistry agrees with Gaussian's own numbers.

## 0.89.26 — 1 November 2026

### Spectrum

- I open outputs up to 256 MB — before it was only up to 32 MB. A 100 MB file takes me a few seconds, and the window keeps answering all that time.

## 0.89.25 — 1 November 2026

### Spectrum

- The «NMR» tab has a «Compute TMS at this level» button: I build a TMS input with the same method, basis and solvent as your calculation. Run it and open it in Spectrum — I remember the reference for that level, and the shifts δ appear for all your results of that level. I no longer apply a reference of another level.

## 0.89.24 — 1 November 2026

### Spectrum

- I checked Spectrum against your ORCA 6.0.1 outputs and found two mistakes. TD-DFT now shows the ground-state energy, with the excited state next to it, separately. And thermochemistry no longer warns «not a minimum» on every ORCA frequency job: the six zeros are translations and rotations, not imaginary modes.

## 0.89.23 — 1 November 2026

### Spectrum

- The IR spectrum has a «Scale factor»: I fill in the frequency scaling factor of the method and basis from the NIST database, and the spectrum comes closer to experiment. CSV tables now open in columns in a Russian Excel too.

## 0.89.20 — 1 November 2026

### Sextant

- When an ORCA optimization does not converge within its cycles, I say so instead of «calculation finished».

## 0.89.19 — 1 November 2026

### Sextant

- I now estimate the time of small calculations more honestly: the start of the program counts, and the estimate agrees with real ORCA runs.

## 0.89.18 — 1 November 2026

### Sextant

- There is «Calculation history» now: I remember the last 60 calculations, open their results, and can watch a calculation on a server again after the program was restarted.

## 0.89.17 — 1 November 2026

### Sextant

- The server window has «Login without a password»: I make a key and write it to the server once with the password; after that no password is needed — on Windows too.

## 0.89.16 — 1 November 2026

### Sextant

- On Windows I find Microsoft MPI for ORCA on several processes myself, and when it is missing I open the page to install it from.

## 0.89.14 — 1 November 2026

### Sextant

- On Windows I put the calculations in a folder with a Latin path: calculation programs there do not open files in folders with Cyrillic letters.

## 0.89.12 — 1 November 2026

### Compass

- The molecule no longer jumps when you switch on building or moving, browse optimization steps and close the panel: the chosen step stays as it was on the screen.

## 0.89.11 — 1 November 2026

- The section menus open smoothly, without a jerk at the start, and a second click on the menu name closes it.

## 0.89.10 — 1 November 2026

### Compass

- In the coordinates table, Delete removes atoms (Backspace on a Mac).

## 0.89.9 — 1 November 2026

### Compass

- The Russian name of «Tidy the geometry» changed; in English it stays the same.

## 0.89.8 — 1 November 2026

### Compass

- Multiwfn on Windows: I run it in the text mode and in a folder with a Latin path, look for the unpacked archive on the Desktop, in Downloads and on the drives, and on an error I show its cause.

## 0.89.7 — 1 November 2026

### Compass

- The manual now has «First steps»: in five minutes with ethanol I show how to open a molecule, measure it, find its symmetry and pass it to a calculation.

## 0.89.6 — 1 November 2026

- I checked the English and Chinese translations of the menus and messages: a few messages were only in Russian; now they are translated.

## 0.89.5 — 1 November 2026

### Compass

- «Display» now has «Hide H atoms»: hydrogens are not drawn in any model but stay in the structure and the calculation. Select a hydrogen to see it.

## 0.89.4 — 1 November 2026

### Compass

- You can now open a structure of up to 2000 atoms, not 500 — a small protein or a cluster, for example. And I read large structures and find their bonds faster.

## 0.89.3 — 1 November 2026

### Compass

- I open structure files the way other programs write them: XYZ with lower-case letters, element numbers and extra columns, files in the old Windows encoding, PDB with alternative atom positions, MOL2 with several molecules. And for a damaged file I say which line is wrong.

## 0.89.2 — 1 November 2026

### Compass

- Undo and Redo no longer lose a step when a preview of the rotation about a bond, the Z-matrix or a calculation step is open: I close the preview first.

## 0.89.1 — 1 November 2026

### Compass

- From SMILES I now build molecules with their real symmetry: SF₆ is an octahedron, PF₅ a bipyramid, allene has perpendicular ends, naphthalene is even, acetophenone and esters are flat. The library holds 106 molecules.

## 0.89.0 — 1 November 2026

### Compass

- The molecule library now holds 101 molecules instead of 65: I added, for example, ozone, carbon monoxide, nitric acid, aniline, styrene, indole, anthracene, THF, dioxane, urea, glycine and alanine.

## 0.88.1 — 1 November 2026

### Compass

- I now find the point group more reliably: no more impossible groups like C4v for ammonia. And if the field holds several molecules, I say that the group is found for a single one only.

## 0.88.0 — 1 November 2026

### Compass

- The menus are now the usual ones: File, Edit, View, Display, Tools and Calculation, and they hold everything that used to be only buttons.
- New: select by numbers or within a coordinate range, expand the selection by one step, put the origin at an atom or the axes on three atoms, turn the molecule to its principal axes, show all bond angles, copy the camera position and the picture itself.
- In Tools I compute moments of inertia and rotational constants, the exact and average molecular mass, and tell you which atoms, bonds and fragments the structure is made of.

## 0.87.12 — 31 October 2026

### Atlas

- When I calculate for more than a second, you see “Calculating…” and the seconds at the bottom, and what I have already calculated I show at once the second time.
- If the connection to the calculations is lost, I say so and offer to try again, and I tell you when it is back.

## 0.87.11 — 31 October 2026

### Atlas

- I pressed every button on every page of the Atlas in three languages. The protein example in “Hückel method” works again, and the empty fields in “Diatomic molecules” and “Atoms in molecules” now tell you what to do.

## 0.87.7 — 31 October 2026

- On the home page I now stand to the right of my greeting.
- The changelog is shorter — I removed the tiny things, and its head now shows the latest entry and the versions of all the sections.
- The Atlas zoom slider is a thin line with ticks, without extra numbers.

## 0.87.4 — 31 October 2026

### Atlas

- The pictures behind the Atlas move with the page, and at the end the book comes up from below.
- Axis titles no longer jump when you move sliders, and drop-down lists open as a neat rounded card.

## 0.87.3 — 31 October 2026

- The Atlas zoom is now above the languages: press the magnifier and a slider slides out right in the panel; press again and it hides.

## 0.87.1 — 31 October 2026

### Atlas

- In the demonstration I no longer fly between blocks — I simply appear next to the right one. And the titles of vertical axes keep clear of the scale numbers.

## 0.87.0 — 31 October 2026

- Windows now appear smoothly instead of popping up, and every table is centred. A pressed button shows it, and a selected one stays blue even under the mouse.

### Atlas

- In the demonstration I fly to the block I am talking about, and I speak faster. The Demonstration button blinks while I am showing — press it again and I stop.
- Blocks are numbered, fractions are written as fractions, and I have more tips — four per topic now — and more terms in the glossary.
- In “Test yourself” I am always the same height, and the density map follows the slider smoothly.

## 0.86.9 — 31 October 2026

- I now meet you in the message windows myself: untangling a ball of thread when something fails, puzzling over an unreadable file, holding a sheet over the bin before deleting, catching conformers with a net and calling “hello?” into a tin can when the server is silent.
- On the empty pages Orbitals, Surfaces, QTAIM, Frequencies and NCI it is me again — with an empty orbital frame or a flag for a critical point. And in Sextant without a molecule I look through a sextant and point to Compass.

## 0.86.8 — 31 October 2026

### Atlas

- I have rewritten my comments in the demonstrations of every topic: now I say not only what is on the screen but also why it matters, and I explain new words right away.

## 0.86.7 — 31 October 2026

### Atlas

- In the demonstration I light exactly what I am talking about, not half the page below, and my bubble now has a blue side.
- In “Test yourself” I appear at once, always in the academic cap.
- In “Vibrations” the arrows point both ways and the atoms are labelled; in “Point groups” molecule suggestions appear only while you type; in “Crystals” I explain the extinctions in more detail.

## 0.86.5 — 31 October 2026

- Some tidying inside: the shared package of the program is now called `azimuth`, not `qcc_studio`, and the settings are stored under the name Azimuth. I moved everything you had set up myself — theme, language, servers and fragments are all there.
- On the home page I now stand at a desk with a book.

## 0.86.3 — 29 October 2026

- The program remembers the folder you last opened a file from: the next «Open…» starts there, not in the home folder.
- The theme chosen last time is saved at once. It was being reset, as it turned out, by the tests: before 0.85.1 they wrote into the settings on your computer and always ended with the light theme. Now the tests have settings of their own.

### Compass

- The «QTAIM» page of the left panel was empty — the page moved from a hidden tab and stayed hidden. Fixed; the difference density Δρ under the list of surfaces is seen again too.

## 0.86.1 — 29 October 2026

### Compass

- Instead of a row of tabs the left panel has a drop-down list, and it holds only what this result has: steps, vibrations, orbitals, surfaces, conformers. The panel is as wide as before again.

## 0.86.0 — 29 October 2026

### Compass

- When the left panel opens, the molecule moves to the right — it no longer hides under it.
- The surfaces have a tab of their own, «Surfaces»: there you choose what to build — from the density and the Laplacian to ELF, NCI and ESP. The «Orbitals» tab keeps the orbitals themselves, their composition and the spin density; the numbers of the table stand right in the middle, and the row of the orbital built is lit.
- The button of what is on the model is blue; press it again — the surface is gone and the button is white again. While I compute there is no waiting window: the cursor becomes a turning ring, and the same ring turns next to the button. And what I have built I remember — the second time I show it at once, with no calculation.

## 0.85.1 — 29 October 2026

- The program was tested on Windows, and I found why the setup stopped there: the list of the teaching files named two pictures that were not in the archive. The list is fixed, and if a file is ever missing, the check now names it and says to download the program again — instead of advising to reinstall Python. The installer writes all its output to setup-log.txt and says at which step it stopped.

## 0.85.0 — 28 October 2026

- Wherever Multiwfn can do the work now, it does: the Laplacian, the spin density, the orbitals, the density — my own arithmetic stays only for when it is missing. And when it is missing, I no longer open a file dialog but say plainly how to install it; the items that need it are grey.
- All the analysis tables now go into one subfolder «Анализ» next to the calculation — the calculation folder no longer drowns in files. The tables are written with «;» and the decimal comma, so that Excel and Numbers in Russian open them at once; the international style is one switch away.
- The same request a second time I take from memory — Multiwfn does not run again. And if an old Multiwfn happens to run, I say so once.

### Compass

- The left panel has a «Surfaces» tab: every surface of Multiwfn in a list by group — the density and its derivatives, ELF and LOL, energy, potential, weak interactions, functions on the molecular surface. Choose a row — «Show», once more — it is gone.
- The list of critical points is shorter: type, atoms, ρ, ∇²ρ and H — what you need to understand a bond. The chosen point is no longer just circled but pulses, so it is seen among the atoms. One button puts the points on the model and takes them off.
- One grid for everything: what is chosen in the menu is chosen in the panel. The menu of the surfaces has fewer repeats, and the two «Wiberg» items in «±» are now told apart: Wiberg of xtb and Wiberg–Löwdin.

### Spectrum

- The detailed table of the critical points moved here, to the «Density topology» tab: coordinates, ε, G, V, |V|/G and the eigenvalues of the Hessian. These are the same points as in Compass: found here — seen there too.
- The NCI plot is here as well, in the «NCI» tab, not a separate window over the model. The maps of «Maps and profiles» show the critical points and bond paths, and for the excitation analysis you can choose which states to compute: all, the chosen ones or only the bright ones.

## 0.84.0 — 28 October 2026

### Spectrum

- The UV-Vis tab has «Excitation analysis»: for every state I look at where the electron leaves from (the “hole”) and where it goes (the “electron”), how far apart they are and how much they overlap — and say whether it is a local excitation or a charge transfer. In benzaldehyde, for example, the weak S₁ at 3.79 eV is the n → π* of the C=O group, and the bright S₃ is local too, π → π*. The table goes into the calculation folder, and the hole and the electron of the chosen state can be seen on the model.

## 0.83.0 — 28 October 2026

### Compass

- More surfaces: «Functions on a grid» — the density, its gradient and Laplacian, kinetic energy, entropy, the total ESP, ALIE, RDG, ELF, LOL; on the molecular surface also ALIE, LEA and LEAE.
- Every surface now leaves a table in the calculation folder: where the function is largest and smallest and at which atom. The ESP summary window is gone — it all goes into files. The QTAIM critical points are written as tables too — nuclei, bonds, rings, cages apart.

### Spectrum

- A new tab «Maps and profiles»: a function in the plane of three atoms — a colour map with contour lines — and along the line through two atoms. On the density profile along a bond the minimum is the bond critical point. The data go into the calculation folder too. The density slices moved here from Compass.

## 0.82.0 — 28 October 2026

### Compass

- Bond orders can be compared now: «±» has «Bond orders: Mayer, Wiberg, FBO, LBO…» — four different definitions, and you can switch between them right on the model. You see how differently the methods “share” the electrons between atoms.
- The orbitals table has a «Composition» column: which atoms make up each orbital and how much. The HOMO of water, for example, is 93 % oxygen.
- Multiwfn builds the orbitals and the density on the model when it is installed: it reads unusual basis sets and core potentials more reliably. Without it I compute them myself, as before.

## 0.81.1 — 28 October 2026

### Compass

- I no longer write on buttons and in menus which program computes an analysis, and no longer show references after every calculation — it is all in the manual, in «External programs and references»: Multiwfn, the analysis methods and the bee colony conformer search.

## 0.81.0 — 28 October 2026

### Compass

- «QTAIM» has a switch above the table: all points, nuclei, bonds, rings, cages — with the number of each. Nuclei are points now too. On the model I show the points of the kind chosen, and circle the row you chose in the table. Every bond point says which atoms it joins: I look at whose nuclei its bond path reaches. That column used to be empty sometimes — fixed.
- New: ELF and LOL from Multiwfn. The surface shows where electrons sit in pairs — bonds, lone pairs, atomic cores: almost a Lewis structure, only computed.

## 0.80.0 — 28 October 2026

### Compass

- The ESP and the critical points are computed by Multiwfn only now. I removed the old ESP map from Mulliken charges and my own point search: Multiwfn computes the potential of the wavefunction itself and finds more points, so two ways side by side only confused. The «ESP» and «Find critical points» buttons stay where they were — they work through Multiwfn when the orbitals were opened from a file.

## 0.79.0 — 28 October 2026

### Compass

- «QTAIM» has a «Multiwfn» button: Multiwfn searches for the critical points, trying all pairs, triples and quadruples of atoms. That finds hydrogen bonds, van der Waals contacts, ring and cage points I could not see before — and the table and the bond paths on the model stay as you know them. On water my search and Multiwfn's agree to the fourth digit.
- The ESP can be seen “for real” now: Multiwfn computes the potential of the wavefunction itself on the molecular surface, and I mark its minima and maxima on it — where to expect an electrophile and where a nucleophile — and show a summary: area, volume, polarity.

## 0.78.0 — 28 October 2026

### Compass

- Now I show weak interactions — the NCI method through Multiwfn: «View → Surface on the model → Weak interactions». Patches appear between the molecules: blue ones are hydrogen bonds, green ones van der Waals touches, red ones where atoms are crowded. Next to them I draw the famous plot RDG — sign(λ₂)ρ: every dip in it is one interaction. The promolecular variant needs no calculation at all — the built structure is enough.

## 0.77.0 — 28 October 2026

### Compass

- I can call Multiwfn for help now. When a result has an orbital file, the «±» menu above the model has «ADCH and CM5 charges (Multiwfn)…»: Multiwfn computes them quietly in the background and I put them on the atoms. Unlike Mulliken charges, they hardly depend on the basis set. Multiwfn has to be installed separately (on a Mac: `brew install multiwfn`) — and cited in your work; I will tell you the references.

## 0.76.0 — 28 October 2026

### Compass

- An empty «Crystal» has me now — in the lower left corner, with a unit cell in my wings. The folder in my bubble opens a CIF file, the little crystal an example. Once a crystal is there I leave until the next start.
- SDF files without a name in the first line (as RDKit, Open Babel and PubChem write them) open again — before, I mixed up the lines and complained of a “wrong counts line”. Files with shifted columns are read too.
- When the bee colony finds no usable structure, I say why — for example, that xtb breaks the C2–C3 bond — and remind you to check the charge and the multiplicity. Most often it is an anion computed as a neutral radical.

## 0.75.0 — 28 October 2026

### Compass

- “Conformer search” has a bee colony (ABC) now: the “bees” fly over the bond turns, and xtb tells them where the energy is lower. First I find the lowest conformer, then low ones unlike it. The method comes from SmartChemDesign/abc; I rewrote it so that nothing extra has to be installed: xtb is enough.

## 0.74.0 — 28 October 2026

### Sextant

- A ready input file of ORCA or Gaussian can now be opened right in Sextant: I take the molecule and the settings from it and run the file itself.
- If a calculation fails, I write what happened and what it may come from — and the stages of the calculation are gathered under the heading “Progress”.
- For a set of structures I can write the input files at once: the same settings, each molecule with its own coordinates, charge and multiplicity.

### Compass

- Several files opened at once, or an SDF database, are now listed on the “Structures” tab of the panel on the left — switch between them with the arrows.

## 0.73.0 — 28 October 2026

### Sextant

- “Additional settings” now has its sections on the left, and the window no longer jumps in size. New: relativistic corrections (DKH2, ZORA, X2C), help for a hard SCF, numerical frequencies, TDA and triplets for TD-DFT — and a new task: excited-state optimization.
- The processes and the memory are right in the setup. The molecule card now tells how many atoms and basis functions there are and roughly how long it will take.
- I connect to the server without windows: a small circle just turns. If the connection drops, I try again every half a minute and ask the VPN to come up myself.

## 0.71.0 — 28 October 2026

### Sextant

- “Calculation window” now sits right on the input file card: “Input file” on the calculation and “Calculation window” on the file — you switch in one place.

## 0.70.0 — 28 October 2026

### Compass

- “Move a whole molecule” selects the molecule you drag at once, so you see what moves. The same with a chain.
- After an optimization the panel opens on the last step; choose another step and fold the panel, and that one stays in Compass (changed your mind — “Undo”).
- In “Orbitals” a second press of “Orbital”, “ρ”, “Spin” or “ESP” takes the picture off the model, and the table now fills the whole panel.
- A new tab “Conformers”: after a search the conformers live there, the arrows switch between them, and any of them can be taken.

## 0.68.0 — 28 October 2026

### Compass

- With two molecules in the field (a dimer, say), “Move a whole molecule” moves the one you drag, and the other stays.
- New moving buttons: “Chain” moves the unbranched piece of a chain up to the nearest branch or ring, and “About a bond”: select two bonded atoms and drag an atom of one side left or right — it turns about the bond.

## 0.67.0 — 28 October 2026

### Sextant

- A calculation now has a name — the “Name” field at the very top. It becomes the first line of the input file and the name of all its files. Leave it empty and I name it myself: formula, method, basis and solvent, for example H2O_B3LYP_def2-SVP_water.inp — so the folder shows at once what is where.
- An optimization takes at most 100 steps by default. Need more or fewer — change it in “Additional settings… → Optimization”.

## 0.66.0 — 28 October 2026

### Sextant

- The calculation no longer opens in a separate window: it takes the place of the input file. “Input file” brings the file back, “Calculation window” the calculation.
- Go to another section and an hourglass appears at the bottom of the left panel; a click shows the progress in a small window that can be hidden. Back in Sextant it closes by itself.
- Less text on the page: what the lines of the input file mean, I tell you behind the “?” next to its title.

## 0.65.0 — 27 October 2026

### Sextant

- An ORCA calculation can now be sent to the laboratory server. Choose “Server” and press “Run calculation”: I log in to the server (I ask for the password only if it does not let me in without one, and remember it until you quit), find out how many cores and how much memory are free there now, and suggest how many processes to take. Then everything is as usual: the calculation window, the stages, and at the end the result comes to your calculation folder.
- While the calculation waits, I say so: “In the queue”. If the connection drops or the VPN sleeps, the calculation on the server goes on — I wait and keep watching. You can close the program: the calculation finishes there.
- The server profile has “Environment lines” instead of the start command; leave them empty and I find ORCA on the server myself. “Check resources” shows what the server has right now.

## 0.64.8 — 27 October 2026

### Atlas

- The topics “Conformers”, “Crystals”, “NMR”, “Heavy elements” and “Walsh diagrams” now show my real portraits instead of the temporary ones.
- In “Test yourself” my reactions are more varied: a thumbs-up, clapping wings, an “oops”, a hint with the pointer and an explanation at the board.

## 0.64.7 — 27 October 2026

### Compass

- While the Compass field is empty, I stand in its lower right corner and say: «Try to build your own molecule ✎ or open a new one 📁». The pencil and the folder can be pressed: the pencil turns on editing, the folder opens a file. Once you have built or opened something, I go away until the next start, leaving a short pale hint in an empty field.

### Sextant

- Sextant is closer to the point: the solvent and the dispersion are right in the setup, the charge and multiplicity in the additional settings, which now open folded and grow when something is unfolded; ORCA got RIJCOSX there. While there is no molecule I wait with a magnifier next to «No atoms yet».
- While a calculation runs I now sit in its window among the papers and count along with the program: I blink, nod and stretch my feet. When the window is hidden, I rest.

## 0.64.6 — 26 October 2026

- The theme switches a little more slowly and smoothly, and the darkness (or light) starts spreading at once, without a slow start.

### Atlas

- The animations of a topic run only while the topic is open: go to another topic or section and the animation freezes, then goes on from the same place.
- The axis titles of the plots are bold and larger, and the title of the horizontal axis stands in the middle.
- In the demo I now wear a teacher’s gown and hold a pointer, and I no longer jerk: when the step changes I fly off at once and appear at the next place with the new text.
- “Postulates”: the section “The five postulates of quantum mechanics”; in section 1 the axes no longer jump, and I explain what t = 0 means; in section 3 the measurement repeats by itself when the precision of the instrument changes.
- “Atomic units”: a clear answer why there are no approximations here. “Hydrogen atom”: step 5 shows the cloud itself. “Hamiltonian”: the last step teaches how to count the terms. “Born–Oppenheimer”: the columns of the tables are even, and the comments no longer merge with the values.

### Compass

- In the empty field I hand you an atom — start with it.

### Sextant

- Sextant has more room: at the top right a small model of the molecule to be calculated (turn it with the mouse) and its formula; below it the input file, which can take the whole column. The launch block is smaller, and in the freed place I put an estimate of the time of the calculation — a very rough one.
- If the calculation program is not found, I look for it with a torch right under the program row and tell you what to do. A failed or stopped calculation and the installation of programs have my pictures too.

## 0.64.5 — 26 October 2026

### Spectrum and Compass

- Orbitals, the density, the Laplacian, Δρ, the critical points and the slice are now computed in a separate thread: the window no longer freezes, the progress bar and «Cancel» answer at once.

## 0.64.4 — 26 October 2026

### Spectrum

- I now read big outputs (over 2 MB) in the background: the window does not freeze while the file is parsed, and the result appears in its tab as soon as it is ready. Small files open at once, as before.

## 0.64.3 — 26 October 2026

### Spectrum

- Thermochemistry no longer breaks at very low temperatures: high frequencies at 10 K used to overflow.
- I now take the multiplicity for thermochemistry from GAMESS, NWChem and Q-Chem outputs too. When it is not in the output, I take 1 and say so instead of keeping quiet.

## 0.64.1 — 26 October 2026

### Compass

- Atoms can have their own labels: select atoms and press the tag button next to «1», «H», «H1». A «#» in the label becomes the number in the order of selection. The labels follow the atoms when you edit the structure and are saved in the project. I label the residues of a protein or DNA from a PDB file myself.
- There is a dummy atom X: a point without a nucleus — for a Z-matrix, the centre of a ring or an axis. It is in the periodic table, written as X in the coordinates, and stays out of the calculation.

### Spectrum

- Orbitals now open right from GAMESS, Firefly, NWChem and Q-Chem outputs — when the program printed them. I checked my Mulliken charges against those each program computes.

## 0.64.0 — 26 October 2026

### Compass

- If an SDF file has many molecules, I open each in its own tab (up to thirty). A PDB file with several models — molecular dynamics frames, for example — goes through as steps in the result panel.
- The «Coordinates» tab now has SMILES and InChI. I ask PubChem for the InChI, so it needs the internet.

### Spectrum

- I now read NWChem, Q-Chem, GAMESS (US) and Firefly results: energies, optimization steps, frequencies with the vibrations, charges, the dipole moment and the TD-DFT spectrum. I checked them on real outputs of these programs from the open cclib set.

## 0.63.3 — 26 October 2026

### Atlas

- You can now page through the topics with the ← and → keys, and ↑ and ↓ scroll the topic. In fields, sliders, the demonstration and the projector mode the arrows work as before.

## 0.63.2 — 26 October 2026

### Compass

- There is no panel to the right of the model any more: everything about the result is in the ☰ panel on the left, in the tabs «Optimization», «Frequencies», «Orbitals» and «QTAIM». In «Frequencies» the chosen vibration moves right on the model — Space pauses it, the arrows pick another one.

### Sextant

- When a calculation ends, I no longer carry you off to another section — the result waits in its tab, and the calculation window has «Go to Compass» and «Go to Spectrum».

## 0.63.1 — 26 October 2026

- Now I am in the program windows too. Before quitting with unsaved changes (and before replacing the project) I hug a folder and ask, and if a calculation is still running I stand in front of the papers with my wings spread. Instead of the system icon, with the same texts.

### Sextant

- When a calculation has finished, I appear in the calculation window with a sheet with a tick. And if the input file seems to have errors, I underline the line with a red pencil.

### Spectrum

- In a tab without a result I study an empty sheet with a magnifier: nothing here yet, and that is fine.

## 0.63.0 — 25 October 2026

### Sextant

- «Run calculation» now lets you choose where to calculate: «This computer» or «Server». For the server fill in your profile in «Server…» — the address, port, login and start command; I do not keep the password and ask for it when connecting. If the server is behind OpenVPN, choose your OpenVPN Connect profile there — I switch the VPN on myself when the server does not answer. Sending the calculation to the server comes in the next version.

## 0.62.0 — 25 October 2026

- The hourglass now sits at the bottom of the left panel, above the languages, and appears only when you have hidden the calculation window: while the window is open, it shows everything anyway.
- The dark theme now spreads from its button over the whole window like an ink blot, and the light one gathers the darkness back into the button. It also switches noticeably faster.

### Compass

- The electron density moved next to the model: after a calculation with orbitals a ☰ button appears on the right above the model — it opens a panel with the orbitals, the density, ESP, the Laplacian, QTAIM and slices. The model stays in view, and you can build one field after another. Press «on the Compass model» in Spectrum and its window gives way to this panel.
- The line under the model, where nothing fitted, is gone: I show short messages right over the model and then take them away. And the «To the calculation settings» button is darker, with an arrow in the style of the other icons.

### Sextant

- The input file can be edited right in Sextant. Before the run I check it and, if I see a mistake, tint the line and ask whether to run it as it is.
- Instead of the window with the end of the output there is a «Program output» button: it opens the output file itself and follows it while the program writes.
- The run card shows the mark of the program and a tick when it is found, without the long path; next to the button only the time of the calculation; «Calculation folder» as an icon. The calculation window shows the formula with subscripts: H₂O. The columns of the page start level again, and the «Own keywords» field is gone — you can edit the file itself now.

## 0.61.0 — 25 October 2026

### Atlas

- «Point groups» opens in full again: the Atlas server no longer loses files when a page asks for all of them at once.

### Compass

- The pencil «Edit the structure» has two icon switches: «Tidy while building» and «Add hydrogens while building». With the second one, put a carbon and you get methane, click it again and you get ethane — I remove the extra hydrogen myself.
- The empty field tells you how to begin: build your own molecule or open a ready one.

## 0.60.0 — 25 October 2026

### Compass

- Computed a molecule in ORCA — the orbitals are there at once: I take them from the .gbw file ORCA leaves next to the output. And «View → Surface on the model» now has «Orbitals and density of this calculation…» and «Electron density analysis…» — right from Compass, without Spectrum.

## 0.59.0 — 25 October 2026

- Tabs are now shared by Compass, Sextant and Spectrum: a tab holds the molecule, the settings of its calculation and the result. Choose a tab in Sextant — it is chosen in Compass and Spectrum too. And from the Crystal you no longer have to go back to the molecule through Compass.
- A calculation result opens in its own tab and right where it is worth looking at: spectra in Spectrum, the rest in Compass. Charges and bond orders are on the model at once, and the orbitals can be opened straight from Compass.
- While a calculation runs, an hourglass turns over in the left panel — you can read the Atlas in peace. Hover over it and I tell you how long it has been running; click and I show the calculation window. When it ends I put a tick next to it.

## 0.58.0 — 25 October 2026

### Spectrum

- The orbital window has «Density analysis…» — the whole electron density. The Laplacian shows where the charge is concentrated: you can see the lone pairs of the oxygen in water. The difference density shows where the electrons went when the atoms bonded. And QTAIM finds the critical points — one for every bond, and one more at the centre of a benzene ring — and draws the bond paths; the table has everything you need to say whether a bond is covalent. And there are slice maps, as in Bader's book.

## 0.57.0 — 25 October 2026

### Compass

- With «3D graphics by VTK» on, the orbitals, the density and the ESP on the model are drawn by it too, together with the atoms. A surface really passes between the atoms, shows through correctly and is no longer cut in two, and its mesh is full — even small orbital lobes are smooth. And it all turns easily.

## 0.56.0 — 25 October 2026

### Spectrum

- There is now an energy diagram of a reaction: put the reactants, the transition state and the products together from your calculation results and see ΔE, ΔH or ΔG, the barriers and the energy of reaction in one picture. I check things for you too: the same atoms and charge in every stage, one level of theory, exactly one imaginary frequency at the transition state. Save the picture as PNG or SVG, and the diagram itself to open it later.

## 0.55.0 — 25 October 2026

- Questions now speak your language all the way: «Save changes?» comes with buttons in the language of the program, not Save and Cancel in English.
- The program icon now looks like the mark on the left panel and changes with the theme. After closing, the Dock keeps the same one — dark if the theme is dark. No more white spots.
- About shows all versions in one line at the top, and the changelog is sorted into tabs: the program, the Atlas, Compass, Sextant, Spectrum.
- The manual is more detailed and has tabs too. Every section has step-by-step «How to…»: build a molecule, find conformers, run a calculation, leave a saddle point.

### Atlas

- The sections are more even: «From calculation to chemistry» split into «Thermochemistry and kinetics» and «Properties and spectra», and «Intermolecular interactions» moved to «Choosing method and basis», next to the superposition error. Every section now has three to five topics.

### Compass

- My “simple springs” learned to twist properly: bonds between tetrahedral atoms are now staggered, and chains stretch into a zigzag — butane is anti by default.
- «Tidy while building»: put an atom or a group and it takes its place at once, while what is already drawn stays put. Even a bare carbon skeleton gets the right angles.
- Molecules from SMILES come as zigzags too, not crumpled.

## 0.54.0 — 25 October 2026

### Atlas

- The Atlas gained topics of the first course: a new page on Walsh diagrams (why water is bent and BeH₂ is not), and in «Point groups», «SCF iterations» and «Hückel method» — SALCs, Koopmans’ theorem, reactivity indices, Fukui functions and semi-empirical methods.

## 0.53.0 — 25 October 2026

### Compass

- VTK now draws straight into the window, on the graphics card, with no copying of the picture. It took a few tries: first the Atlas went black and Compass crashed. Three small check scripts on your Mac found both causes: the window with the Atlas was composed with Metal, where an OpenGL widget is not shown, and VTK tripped over the way its context was switched. Now, with «3D graphics by VTK» chosen, after a restart the whole program composes its windows with OpenGL and VTK draws right in the Compass field. Without VTK everything is as before.

## 0.52.0 — 25 October 2026

### Compass

- «Compass · Molecule» and «Compass · Crystal» now have their own tabs: molecules live in «Molecule», crystals in «Crystal», and they no longer drop in on each other. Go to the other subsection and back — what you left is still there.

## 0.51.1 — 25 October 2026

### Compass

- The VTK 3D graphics can now be turned on in «Compass · Molecule» too.
- PubChem should answer again: the culprit was not the internet but Python’s certificates. If something goes wrong, I now say what exactly.

## 0.51.0 — 25 October 2026

### Compass

- Compass can try new 3D graphics: «View → 3D graphics by VTK (trial)». VTK then draws the atoms and bonds, and everything else stays as before. If VTK does not work on your computer, I will say so and everything goes back to how it was. Compare the picture and the speed and tell me how it went!

## 0.50.1 — 25 October 2026

### Atlas

- The Atlas has more dotted words: I brought over the whole course glossary — 131 terms instead of 56, from the operator and the particle in a box to the σ-hole and the Woodward–Hoffmann rules. Click a word for its definition and a link to its topic.
- In «Heavy elements» I added a hint on which basis to give a heavy atom with DKH or ZORA: the DKH-def2 and ZORA-def2 sets stop at krypton.

## 0.50.0 — 25 October 2026

- «Continue» on the home page shows the Atlas topic by its title at once, not by a short id like «cf»; the section cards on the home page are two even columns.

### Atlas

- The Atlas has four new topics: NMR, conformers, heavy elements and crystals — with calculations, exercises and my facts. Small ‹ › arrows step between topics, and pages with molecules now have «Open in Compass» buttons.
- My picture on the topic pages no longer jumps when you switch topics, and all my pictures are ten times lighter.
- In the Atlas I no longer fly across the page: in the demonstration and in «Check yourself» I appear right in my place.

## 0.49.0 — 25 October 2026

- A tidy-up: the program moved out of QCСC to «Documents/Azimuth-программа»; calculations stay in «Documents/Azimuth/Расчёты».
- My old poses and animation frames are in «Documents/Квил_архив» now — the program keeps only the pictures it shows.

## 0.48.0 — 24 October 2026

### Sextant

- In Sextant methods and basis sets are chosen by families now — the list no longer runs off the screen.
- I work out the charge and multiplicity from the molecule myself. Change them and I'll tell you what the structure expected.
- I check how many cores and how much memory the computer has and suggest how much to take. I also suggest a method and basis set for the molecule and task — and explain why.
- For those who like to turn the knobs: convergence, grid, transition state search, Hirshfeld charges, temperature and even your own keywords.

## 0.47.0 — 24 October 2026

- The menus got slimmer and tidier, and everything about calculations moved to the «Calculation» menu.

### Atlas

- On the Atlas home page I am bigger now, and I have 114 facts — three for every topic.

### Compass

- Compass has new icons: the needle points at a molecule or at a crystal. And molecules drawn in thin lines now float on the panel.
- Under the model you now see just the formula and the number of atoms. I name the molecule and its point group when you press the button — calmer and faster.

## 0.46.0 — 24 October 2026

- Buttons became icons that unfold when you hover over them. And Sextant has an arrow back to the molecule.

### Compass

- Compass has tabs now! A result opens in its own tab while your molecule waits calmly in the first one. Close the steps drawer — the result is still there.
- A calculation started from Sextant comes back to the tab it was sent from.
- There are two Compasses now: «Molecule» and «Crystal». Open a CIF and I’ll move to crystals myself.

## 0.45.0 — 24 October 2026

### Sextant

- More methods and basis sets, and I show only those the chosen program knows: Gaussian has its ωB97X-D, ORCA ωB97X-D3 and r2SCAN, and Gaussian has no pcseg at all.
- The rarer settings — solvent, dispersion, memory — are hidden in «Additional settings…», so the page stays calm.
- A started calculation now lives in its own window, which minimizes together with the program. The «Run» button turns grey meanwhile — no pressing it twice.
- ORCA on two cores on a Mac fell with «Library not loaded: libmpi.40.dylib»: macOS wiped the library path on the way. Now I put it back.

## 0.44.0 — 24 October 2026

### Sextant

- ORCA wants several cores but there is no Open MPI? One button and I’ll put Open MPI 4.1 into the program folder myself. I can install xtb and CREST along the way. No terminal needed.

## 0.43.0 — 24 October 2026

### Compass

- Conformers are now sorted by CREST's rules: a 6 kcal/mol window, repeats removed, and the same molecule with shuffled atom numbers counted as a rotamer — butane's gauche+ and gauche− became one conformer «in two copies».
- If you have CREST installed, I’ll run CREST itself: it searches longer but finds more.

## 0.42.0 — 24 October 2026

### Compass

- Conformer search: I turn every rotatable bond, throw away the structures where atoms run into each other and show what is left. Butane gives anti and two gauche, as in the textbook.
- «Refine with xtb» orders the conformers by energy and tells the share of each at room temperature. Anti butane wins, of course.

## 0.41.0 — 24 October 2026

### Compass

- Compass can build a path between two structures: give it the start and the end of a reaction and I’ll place the frames in between. The atoms in the end file can come in any order — I’ll count them again myself.
- IDPP takes care of the bonds: when a group turns, the atoms go along an arc instead of cutting the corner.

### Sextant

- The path can go straight to ORCA: the task “Reaction path (NEB-CI)” finds both the path and the transition state.

## 0.40.0 — 24 October 2026

### Compass

- Orbitals moved right onto the molecule: the blue and red phases wrap the atoms in Compass and turn with the model.
- There is an electrostatic potential map: red where the molecule likes protons, blue where it likes electrons. In water the oxygen goes red and the hydrogens blue — just as in the textbook.
- The level of the surface and its transparency are in «View → Surface on the model».

## 0.39.0 — 24 October 2026

- You can simply drop a file on the window. I’ll catch it.

### Compass

- Crystals got surfaces: give (hkl), the layers and the vacuum, and rock salt lays its (111) face right in the plane of the screen. The slab can be saved as CIF.
- The Z-matrix can now be edited as numbers: make a bond longer and the molecule changes at once without running away.
- “Standard view”: along the axes, along a bond or straight onto the plane of three atoms. Benzene face-on — here you go.
- Pictures for a paper as SVG and PDF, with vector labels and arrows.

## 0.38.0 — 24 October 2026

### Compass

- The steps of an ORCA optimization now show the forces on the atoms: the arrows get shorter and shorter — the molecule is calming down.

### Spectrum

- Spectrum now does thermochemistry: enthalpy, entropy and Gibbs energy at any temperature. I checked the numbers against Psi4 — they agree to the eighth digit. That felt good.
- A new “Convergence” tab: you see how the gradients fall step by step and which criterion stays stubborn the longest.
- Spectra can be compared: “Compare with…” lays a second IR or UV-Vis spectrum dashed over the first. B3LYP versus PBE0 — place your bets.
- Spectrum learned to read the excited states of Psi4.

## 0.37.0 — 24 October 2026

### Sextant

- Sextant became a polyglot: besides ORCA and xtb it writes and runs Gaussian and Psi4. One molecule, four programs — compare away.
- Molecules can now take a dip in a solvent: water, methanol, DMSO, chloroform and eight more. Molecules in water behave differently — see for yourself.
- D3(BJ) and D4 dispersion: without it two benzenes barely notice each other, with it they stick together, as they should.
- New tasks: the UV-Vis spectrum (TD-DFT) and NMR. Compute, then look at the bands and shifts in Spectrum right away.
- If a program cannot do something, I’ll say so honestly and tell you whom to ask instead.

## 0.36.0 — 24 October 2026

### Sextant

- Sextant no longer just writes input files — it runs ORCA or xtb itself! Press “Run calculation” and I keep an eye on the time, the optimization cycles and the energy. When it ends, the result opens by itself: steps in Compass, everything else in Spectrum.
- xtb (GFN2-xTB) is a fast semiempirical method: geometry and frequencies in seconds. Just right for a first guess.
- I look for the program myself: ORCA folders, Homebrew, conda. If I can’t find it, show me with “Choose…” and I’ll remember.
- Every calculation lives in its own folder in “Documents/Azimuth/Расчёты”. “Stop” stops everything, even the processes ORCA managed to spawn.

## 0.35.0 — 23 October 2026

- I still say hello on the program’s home page. Saying hello is my favourite thing.
- The sidebar went from black to dark blue, like the night sky over an observatory, and the program icon took off its background — it suits it better. The header grew a little, the panels got denser.
- About now has a manual and the versions of all sections. Compass, Sextant and Spectrum got their first numbers — 1.0.0. Congratulations!
- The examples folder now has plenty to practise on: real calculations, crystals, pairs of structures and my fragments. «File → Open an example…» — off you go.

### Atlas

- I moved! My tips now live on the Atlas home page: I peek from behind a card and suggest what to try. If I get annoying, press “Hide” — no hard feelings (until tomorrow).
- “Try it yourself” is now “Check your knowledge”: no more typing numbers, just pick one of four answers. You may guess, but I see everything.
- The postulates page had five postulates and three sections. Mathematics objected, so now there are five sections.
- The hydrogen atom no longer looks like a picture from a 1995 video game: the cross-section and the cloud are drawn at full resolution, and the nodes are smooth.
- The variational method no longer lets its point escape over the edge of the graph. The point was very variational, but we came to an agreement.

### Compass

- Charges, bond orders and the dipole moment from a calculation are drawn right on the molecule in Compass.
- Bonds in Compass honestly enter the atoms, and rotation is four times faster. Benzene no longer stops to think.
- Compass has a library of 65 molecules and IUPAC names in three languages. I checked 94 names — none of them took offence.
- Compass can now lay two structures over each other, even if the atoms are numbered any old way: I work out who matches whom and tell you the RMSD. I won’t mix up enantiomers — I don’t use a mirror without asking.
- Your own fragments: select a group, save it — and it lives in «My fragments» next to methyl and phenyl. You can hand it to a colleague as a file.
- Bonds now turn like a grown-up program: an exact dihedral, with the mouse or as a scan with a step. I’ll tell you where the atoms bump heads.
- Display schemes have arrived: one click for a white background for a paper, black-and-white printing, Jmol colours or a presentation with big atoms. And your favourite look can be saved under its own name.
- Compass opens CIF files: the unit cell, a block of cells and the a, b, c edges. Rock salt looks just like the textbook — 14 sodiums and 13 chlorines in one cell, I counted.

### Spectrum

- Spectrum learned three new languages: Gaussian, xtb and Psi4. ORCA is not jealous.
- Orbitals can now be seen without CUBE files: everything is computed straight from Molden, fchk or an ORCA output. UV-Vis and NMR spectra, potential energy surface scans and the IRC path are here too.
- Vibrations went to the movies: a GIF of one period, XYZ frames and arrows both ways. And an imaginary frequency can now be given a push — the displaced geometry goes straight to Compass.

## 0.34.0 — 22 October 2026

### Compass

- Compass labels the lengths of all bonds, and the ruler pins the distances and angles you need to the model.
- Pictures: PNG, high resolution, a transparent background and even GIFs — the molecule rotating and the optimization steps. Time to make movies.
- The trackpad understands gestures: a swipe rotates, two fingers pan, a pinch zooms.
- The molecule turns in screen axes: the near side follows the mouse however it was turned before.

## 0.30–0.33 — 22 October 2026

- Frame selection with Shift. The Dock icon follows the system theme, like every well-mannered application.

### Compass

- Compass finds the point group and puts the molecule in the standard orientation with one button.
- New formats: SDF, MOL2, PDB, Gaussian and ORCA input files. “Tidy the geometry” and “Add hydrogens” keep things in order.
- Z-matrices and optimization constraints arrived — a little padlock, and the atom stays put.

## 0.25–0.29 — 21–22 October 2026

- Compass, Sextant and Spectrum started speaking English and Chinese; the menus moved into the header.
- Back and Forward buttons, the system theme on the first start, pale azimuth and sextant scales in the background.
- The home page got the “Continue” cards — so you don’t have to look for where you stopped.

### Compass

- Optimization steps moved to Compass: the molecule itself shows how it looked for the minimum.

## 0.19–0.24 — 21 October 2026

- The program got a home page and a motto, “Your guide to quantum chemistry”. I settled there and learned to blink.

### Atlas

- The Atlas became part of the program: one theme and one language for everything. The About window appeared.

## Earlier

- It all started with Compass, Sextant and Spectrum — and a great love of quantum chemistry. The details are in CHANGELOG.md.
