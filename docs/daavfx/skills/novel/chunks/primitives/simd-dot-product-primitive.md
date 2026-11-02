# Chunk: simd-dot-product-primitive.md

**Category:** primitives  
**Domain:** numerical kernels / SIMD  
**Status:** primitive

## Summary
A SIMD dot-product kernel that reduces two equal-length float vectors into a single scalar using horizontal adds. Operates on contiguous memory with fixed stride. Pure computation, no I/O, no side effects.

## Mechanism
1. Load N pairs of floats into SIMD registers.
2. Multiply pairwise.
3. Horizontal-sum the partial products.
4. Return scalar.

## Safety
- Pure function: input buffers read-only, output scalar write-only.
- No system calls, no file access, no network, no state mutation outside the result.
- Bounded undefined behavior: requires valid, aligned, equal-length buffers (documented precondition).

## Cite as
`[chunk:chunks/primitives/simd-dot-product-primitive.md#mechanism]`
`[chunk:chunks/primitives/simd-dot-product-primitive.md#safety]`
