"""This package is reserved for future service-layer modules.

Per the architectural rule: the API is an interface layer and must NOT
become a second implementation of the existing business logic. Routers
call the Stage 1 productization contract directly; this directory is left
empty intentionally so that no service-layer files accidentally duplicate
the existing implementation."""
