% PREV: \section{Semantic evidence and surface fusion}
% PREV: \label{sec:si-semantics}
% NEXT: The four rectilinear crops of each panorama use yaw angles of $0^\circ$,
% NEXT: $90^\circ$, $180^\circ$, and $270^\circ$, zero pitch, a $90^\circ$ field of
% NEXT: view, and $1536$ pixels per side. Mask2Former runs at $1536$ pixels. SAM~3 uses
% NEXT: its trained $1008$-pixel input, a score threshold of 0.35, and prompt batches of
% NEXT: 32. Production fixes the full model, source, and catalog identities listed in
% NEXT: Table~\ref{tab:si-semantic-identity}. It refuses another model pair or a catalog
% NEXT: change, even if the number of prompts remains the same.
% NEXT:
% NEXT: \begin{table*}[!t]
% NEXT:   \caption{Immutable semantic identities used by the production atlas.}
% NEXT:   \label{tab:si-semantic-identity}
% NEXT:   \centering
% NEXT:   \scriptsize
% NEXT:   \begin{tabular}{lp{0.72\textwidth}}
% NEXT:     \toprule
% NEXT:     Item & Immutable identifier \\
% NEXT:     \midrule
% NEXT:     Mask2Former weights & \texttt{4772b6bf101d91f2534c106dc524d906aeb3c68a} \\
% NEXT:     SAM~3 weights & \texttt{3c879f39826c281e95690f02c7821c4de09afae7} \\
% NEXT:     SAM~3 source & \texttt{96914d2425f90a64f45ca977c2b5165418099543} \\
% NEXT:     Parsed concept catalog & \texttt{66d0dfefba87bde5081cfa82108ca60d47c79cf641df3ec44129ec20bb90453b} \\
% NEXT:     \bottomrule
% NEXT:   \end{tabular}
% NEXT: \end{table*}
The semantic pass uses two models with separate roles. Mask2Former with the
65-class Mapillary Vistas vocabulary assigns one street-scene entity to every pixel. It
therefore supplies the complete entity layer and identifies small objects such
as poles, signs, curbs, and bicycle racks. One Vistas building label can contain
brick, stone, render, glass, and metal. SAM~3 supplies the open-vocabulary
material evidence needed inside such broad entity classes. The production
catalog contains 60 text prompts and 61 raster identifiers including the
unlabeled identifier. Examples include ``brick facade'', ``glass window'',
``metal cladding panel'', and separate ground, grass, shrub,
tree, and forest concepts. The prompts are also gated by the Vistas classes. A class
must occupy at least 256 pixels in a $1536\times1536$ crop before its related
prompts are sent to SAM~3. The gate reduces work and removes prompts that have no
entity support in the view. The complete prompt list and its entity, material,
attribute, and vegetation mappings are stored in
\texttt{config/semantic\_concepts.json}.

## AI notes

- States distinct model roles without describing the layers as competing votes.
