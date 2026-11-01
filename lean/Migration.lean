import Std

namespace OwedMigration

-- A finite bijective reindexing is represented by a permutation of the list.
-- This is a model theorem; SQLite conformance is checked separately at runtime.
theorem conservation (xs ys : List Int) (h : xs.Perm ys) : xs.sum = ys.sum := by
  induction h with
  | nil => rfl
  | cons a _ ih => simp [List.sum_cons, ih]
  | swap a b l => simp [List.sum_cons]; omega
  | trans _ _ ih₁ ih₂ => exact ih₁.trans ih₂

-- Source owners 0,1; authoritative destination is the same index.
def balance (i : Bool) : Int := if i then 30000 else 70000
def wrong (i : Bool) : Int := balance (!i)

theorem insufficient_total :
    ([balance false, balance true].length = [wrong false, wrong true].length) ∧
    ([balance false, balance true].sum = [wrong false, wrong true].sum) ∧
    wrong false ≠ balance false := by decide

-- A bijective correspondence has a two-sided inverse. The implementation model
-- looks up the source via that inverse; the desired balance equality is derived.
theorem ownership {Source Destination : Type} (balances : Source → Int)
    (crosswalk : Source → Destination) (inverse : Destination → Source)
    (leftInverse : ∀ s, inverse (crosswalk s) = s)
    (_rightInverse : ∀ d, crosswalk (inverse d) = d) (s : Source) :
    (fun d => balances (inverse d)) (crosswalk s) = balances s := by
  exact congrArg balances (leftInverse s)

#check conservation
#check insufficient_total
#check ownership
#print axioms conservation
#print axioms insufficient_total
#print axioms ownership
end OwedMigration
