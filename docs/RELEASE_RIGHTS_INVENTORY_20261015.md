# Release rights inventory — 2026-10-15

## Decision

The committed source snapshot `87668c7806f8b9aea48494cddb9a8bc96277ddac`
(tree `c82bdf144a3fb204549b1bd7dd00556c5bcdae5f`) has been partitioned
mechanically into mutually exclusive rights-review classes. The
machine-readable record is `experiments/release_rights_inventory_20261015.json`.
Binding the source commit avoids the impossible self-reference that would arise
if a report containing its own digest claimed to describe the index after that
report was written.

The bound Git tree contains 825 entries:

- 792 first-party candidates that still require author confirmation of ownership or permission;
- 21 generated manuscript figures or source-data artifacts whose rights follow their source code and data;
- 11 source-metadata manifests that identify upstream material but do not grant rights to it; and
- one external gitlink, `vendor/solver-in-the-loop`, which remains separately licensed upstream and is not vendored into the main history-free snapshot.

There are zero tracked restricted paths, zero tracked `private` paths, and zero tracked symbolic links requiring target review. There is also no root `LICENSE`, `COPYING`, or `NOTICE` file.

## What this closes

This closes the path-inventory problem for the bound source snapshot: every
tracked entry has one release-review class, the class counts sum exactly to the
825-entry tree, and the tree-entry and path-set identities are content hashed. It
confirms that source metadata and the external submodule are not silently
treated as first-party code.

## What remains an author decision

The inventory does not infer ownership from repository location. The authors
must confirm the 792 first-party candidates, select a root license, approve a
third-party attribution/NOTICE policy, retain source-specific provenance for
all 11 metadata manifests, and authorize the final public release. Generated
figures and tables may be released only under the rights and disclosure
constraints of their underlying evidence.

No file content, credential, model/API endpoint, solver, or network service was read or executed by this inventory.
