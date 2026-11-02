# Chunk: weight-quantization-lookup-table.md

**Category:** abandoned_artifacts  
**Domain:** model compression / inference  
**Status:** shelved

## Summary
A per-layer weight quantization lookup table that maps full-precision weights to 8-bit codes at inference time. Built to reduce memory footprint but shelved because no one found a use case where memory was the binding constraint.

## Mechanism
1. Train/calibrate a codebook of 256 representative weight values per layer.
2. At inference, replace each weight with its nearest codebook index.
3. Dequantize on the fly via index->value table lookup during dot products.

## Why it was shelved
The team had ample RAM; quantization was a solution without a problem. The mechanism itself is sound.

## Repurposing opportunity
The lookup-table + dequantize-on-read pattern can be recombined with the SIMD dot-product primitive: dequantized weights feed directly into SIMD reduction, yielding a memory-bandwidth-bound inference kernel. Purpose-agnostic: ships as a standalone quantized-inference primitive even if no immediate consumer exists.

## Cite as
`[chunk:chunks/abandoned_artifacts/weight-quantization-lookup-table.md#mechanism]`
`[chunk:chunks/abandoned_artifacts/weight-quantization-lookup-table.md#repurposing-opportunity]`
