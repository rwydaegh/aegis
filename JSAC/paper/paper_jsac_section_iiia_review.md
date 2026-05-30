# Section III.A `w*` equation — issue

`eq:closedform` on line 419 is inconsistent with `eq:KKT` in the appendix.

## The discrepancy

The actual KKT stationarity (line 1279–1283) is

$$\bigl(\mathbf{Q}_{\mathrm{tot}}(\boldsymbol\lambda) + \nu\mathbf I + \sum_{k'} u_{k'}|v_{k'}|^2 \mathbf{h}_{k'}\mathbf{h}_{k'}^H\bigr)\mathbf{w}_k = u_k v_k\,\mathbf{h}_k.$$

The body equation drops the inter-user interference Gram
$\mathbf H := \sum_{k'} u_{k'}|v_{k'}|^2\mathbf{h}_{k'}\mathbf{h}_{k'}^H$
from the matrix:

$$\mathbf{w}_k^\star = (\mathbf{Q}_{\mathrm{tot}} + \nu\mathbf I)^{-1}\mathbf{g}_k.$$

## Why the appendix's justification doesn't hold

The appendix tries to wave this away (line 1284–1287): *"Folding the
inter-user interference term into a redefined drive
$\mathbf{g}_k = u_k v_k \mathbf{h}_k$ and a slightly modified denominator..."*
That sentence is wrong on both halves:

1. $\mathbf H\mathbf{w}_k$ is a matrix acting on $\mathbf{w}_k$. You cannot
   fold it into the RHS — moving it across the equality would give
   $\mathbf{g}_k - \mathbf H\mathbf{w}_k$, which still contains $\mathbf{w}_k$,
   so it isn't a closed form.
2. The "redefined drive" stated is $\mathbf{g}_k = u_k v_k \mathbf{h}_k$ — i.e.
   unchanged from the KKT RHS. So nothing was actually folded in.
3. Saying $\mathbf{Q}_{\mathrm{tot}}$ "inherits the interference contribution"
   silently redefines the symbol whose definition is fixed in `eq:Qtot` at
   line 408 as $\sum_u \lambda_u \mathbf{Q}^{(u)}$. Same name, two meanings.

## ZF rank-one limit makes the gap visible

With $\boldsymbol\lambda = 0$ and the body's formula,
$\mathbf{Q}_{\mathrm{tot}}=0$ and
$\mathbf{w}_k^\star\propto\mathbf{g}_k = u_k v_k \mathbf{h}_k$ — that's MRT,
not regularised ZF. Regularised ZF needs
$(\sum_{k'}\mathbf{h}_{k'}\mathbf{h}_{k'}^H + \nu\mathbf I)^{-1}\mathbf{h}_k$,
which only appears if $\mathbf H$ is in the matrix. The remark on
line 432–440 implicitly assumes $\mathbf H$ is there.

## Two clean fixes

- **A (preferred, honest):** write `eq:closedform` with the full denominator

  $$\mathbf{w}_k^\star = \bigl(\mathbf{Q}_{\mathrm{tot}}(\boldsymbol\lambda) + \mathbf H(\{u_{k'},v_{k'}\}) + \nu\mathbf I\bigr)^{-1} u_k v_k\mathbf{h}_k,$$

  and note $\mathbf H$ is the standard WMMSE inter-user Gram,
  $k$-independent.

- **B (compact):** introduce a single symbol, e.g.

  $$\widetilde{\mathbf{Q}}_{\mathrm{tot}}(\boldsymbol\lambda;\{u,v\}) := \mathbf{Q}_{\mathrm{tot}}(\boldsymbol\lambda) + \mathbf H,$$

  define it at `eq:Qtot`, and use it in the boxed equation. Then the
  appendix sentence becomes accurate.

Either way the appendix paragraph at 1284–1287 needs rewriting — there's
no scalar trick that legitimately collapses `eq:KKT` onto the current
`eq:closedform`.
