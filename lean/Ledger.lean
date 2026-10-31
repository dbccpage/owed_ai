import Std

namespace AnomalonLedger

def InModel (a b : Int) : Prop := 0 ≤ a ∧ a ≤ 120 ∧ b = 100 - a
def Q (a b : Int) : Int := a + b
def P (a b : Int) : Bool := decide (0 ≤ a ∧ 0 ≤ b)

theorem witness_membership : InModel 80 20 ∧ InModel 120 (-20) := by
  unfold InModel
  decide

theorem observation_ambiguity : Q 80 20 = Q 120 (-20) ∧ P 80 20 ≠ P 120 (-20) := by
  decide

theorem no_total_decider :
    ¬ ∃ d : Int → Bool, ∀ a b : Int, InModel a b → d (Q a b) = P a b := by
  intro ⟨d, h⟩
  have positive := h 80 20 (by unfold InModel; decide)
  have negative := h 120 (-20) (by unfold InModel; decide)
  change d 100 = true at positive
  change d 100 = false at negative
  rw [positive] at negative
  cases negative

theorem extra_observation_suffices (a b : Int) (h : InModel a b) :
    P a b = decide (0 ≤ b) := by
  simp [P, h.1]

#check witness_membership
#check observation_ambiguity
#check no_total_decider
#check extra_observation_suffices
#print axioms witness_membership
#print axioms observation_ambiguity
#print axioms no_total_decider
#print axioms extra_observation_suffices

end AnomalonLedger
