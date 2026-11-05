# Start here: the total was right

## Predict first

A bank moves three customers' accounts to a new system. Before the move the three
balances add up to $300. After the move they still add up to $300, and there are
still three accounts.

Did every customer keep their own money? Write down yes, no, or "can't tell".

## Try it

Before: Ana $50, Ben $100, Cy $150.

After: Ana $150, Ben $100, Cy $50.

Add both columns. Count both columns.

## What happened

Both totals are $300 and both counts are 3, yet Ana and Cy swapped balances. The
checks passed and the move was still wrong. The right answer to the question was
"can't tell": a total and a count say nothing about who owns which dollar.

To know that each customer kept their money you need one more thing: a record
saying which old account became which new account. Without it, several different
moves look identical to the checks.

## What Owed does

Owed runs a small, made-up version of this move. It shows which checks passed,
names what those checks cannot tell apart, and says what record is still missing.
When the record is supplied, Owed checks the repaired move against it and shows
the result. When the record is missing, outdated or contradictory, Owed refuses to
call the move correct.

The name comes from that last step: what has been checked, what is supported, and
what is still owed.

## Check yourself

1. Two accounts, $40 and $60, become $60 and $40. Do the total and count change?

<details><summary>Answer</summary>

No. Total $100 and count 2 both times, but the balances swapped.

</details>

2. What single piece of information would settle whether the move was right?

<details><summary>Answer</summary>

The record of which old account became which new account.

</details>

## What this page does not claim

| Claim | Kind |
| --- | --- |
| Equal totals and counts do not show that each owner kept their balance | Fact about the example, checked by hand |
| The customers and amounts are real | No. They are made up |
| Owed proves real bank migrations correct | No. It checks a small made-up case against the records it is given |

## Where next

Level 2 walks through the live demo screen by screen.
