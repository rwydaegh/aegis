% NEXT: The semantic pass uses two models with separate roles. Mask2Former with the
% NEXT: 65-class Mapillary Vistas vocabulary assigns one street-scene entity to every pixel. It
% NEXT: therefore supplies the complete entity layer and identifies small objects such
% NEXT: as poles, signs, curbs, and bicycle racks. One Vistas building label can contain
% NEXT: brick, stone, render, glass, and metal. SAM~3 supplies the open-vocabulary
% NEXT: material evidence needed inside such broad entity classes. The production
% NEXT: catalog contains 60 text prompts and 61 raster identifiers including the
% NEXT: unlabeled identifier. Examples include ``brick facade'', ``glass window'',
% NEXT: ``metal cladding panel'', and separate ground, grass, shrub,
% NEXT: tree, and forest concepts. The prompts are also gated by the Vistas classes. A class
% NEXT: must occupy at least 256 pixels in a $1536\times1536$ crop before its related
% NEXT: prompts are sent to SAM~3. The gate reduces work and removes prompts that have no
% NEXT: entity support in the view. The complete prompt list and its entity, material,
% NEXT: attribute, and vegetation mappings are stored in
% NEXT: \texttt{config/semantic\_concepts.json}.
\section{Semantic evidence and surface fusion}
\label{sec:si-semantics}

## Reviews

_(empty)_
