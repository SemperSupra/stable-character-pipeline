# R014 secondary-motion controller RDT&E (research, not soft-body physics validation)

This independent numerical batch builds a deterministic, bounded, damped secondary-motion controller and a signed morph-weight adaptor. It is suitable as an **animation driver experiment** only. It does not attach to a real anatomical mesh; its region material numbers are illustrative, not measured tissue constitutive properties.

Qualification requires future R014 integration with actual MPFB/MHR topology, tissue region masks and skin weights, localized volume changes, contact/penetration constraints, temporal quality, photographed anatomical references and independent review. In particular, pelvis/perineal surfaces are an independently configurable adult-anatomy region, not a biologically calibrated solver or a medical claim.

All test inputs are synthetic numeric arrays, no personal or private imagery. No build host contamination or GPU. Work independently and keep this PR draft and unmerged until reviewed by private issue #138.
