# Windows laptop callback design

Topology design, not a qualified owner-laptop setup or a working bank authorization flow. Later isolated implementations now include a TLS relay with native Windows synthetic tests, DPAPI storage with synthetic runner tests, and a cooperative Python lifecycle helper. None supplies the complete linking workflow or connects the MCP to a real bank. See ENABLE_BANKING_REDIRECT_TLS.md, WINDOWS_PRIVATE_STORE_NOTES.md and windows-tls-relay/SUPERVISOR_NOTES.md for their separate evidence and limits. The exact Production redirect remains unconfirmed.

## Selected topology

Both programs run on the owner's Windows laptop:

Windows browser -> short-lived Windows TLS listener at `https://localhost:8765/callback` -> fixed local HTTP endpoint at `127.0.0.1:8766` -> separate local admin workflow.

No SSH, Linux backend, public callback, public relay, VM or MACD host deployment is part of this plan. No inbound LAN port is needed. The MCP read-only tools do not start authorization, receive callback codes or expose admin operations.

The two-process boundary is local isolation, not authentication against other processes running as the same Windows user. Loopback does not make a port private from local applications. Review whether a per-attempt private channel between the TLS relay and admin process is required before enabling the real workflow. Do not solve local interception by exposing a network service.

## Windows TLS and certificate gate

The intended relay uses Windows certificate APIs and .NET SslStream, retrieving one certificate from `Cert:\CurrentUser\My` by its exact thumbprint. Its private key should be non-exportable. The certificate should have SAN localhost and Server Authentication usage, be a non-CA leaf and be short-lived. These properties and browser compatibility remain to be verified on the target Windows version.

Creating a certificate and placing it in a trusted root store changes local trust. Explain the change and obtain permission before doing it. Trust only the exact reviewed leaf certificate, not a general-purpose development CA. A store entry does not cryptographically restrict trust to a port. Never disable certificate checks or click through a browser warning as a workaround. Do not export the private key.

The reviewed implementation must include exact creation, use and removal steps. This document deliberately contains no executable certificate installation script. Do not install a development CA or mkcert as a shortcut. Microsoft documents certificate creation, public-certificate export and store import; those primitives do not establish provider acceptance of this design.

## Admin storage gate

The original private_store.py remains POSIX-only and refuses native Windows. A separate windows_private_store.py now implements current-user DPAPI with synthetic native runner evidence; see WINDOWS_PRIVATE_STORE_NOTES.md. It does not inspect or repair inherited ACLs, prevent concurrent hostile path swaps, qualify backups or connect storage to the bank workflow. Before real secrets or sessions can persist, review those limits and verify the intended target-laptop account binding, permissions, recovery and integrated lifecycle. Do not substitute an ordinary plaintext file.

Synthetic callback tests can use temporary non-secret fixtures. Do not create a real application key or ask the owner to link a bank until the storage and complete workflow are ready and separately approved.

## Relay requirements

- Explicit IPv4 loopback binds only. Browser localhost may resolve IPv6 first, so test the actual browser or add a reviewed IPv6 loopback-only listener. Never bind all interfaces to work around resolution.
- Fixed callback path and origin, bounded request line and headers, bounded TLS handshake/read time, one-attempt lifetime. No arbitrary proxy destination.
- Only the expected query fields reach the fixed local endpoint. State and authorization code never appear in access logs, exception output, shell history, screenshots, tool results or command arguments.
- State is generated per attempt, checked in constant time, expires using a monotonic clock and is consumed exactly once. Denial/cancellation/expiry close the attempt. TTL is separate from bank consent duration.
- Return constant no-store, no-referrer, restrictive-CSP HTML with no external assets. Never echo provider bodies, codes or state.
- Stop both listeners after completion or failure and verify ports are closed. Timeout after a provider POST may mean remote state exists. Do not retry blindly.

## Required verification before a real flow

1. Provider confirms the exact registered redirect, localhost versus127.0.0.1, certificate and port restrictions.
2. Synthetic end-to-end TLS callback passes on the actual Windows/browser version, with no warning bypass. Negative tests cover wrong Host/path/state, replay, duplicate parameters, oversized/slow requests and expiry.
3. Both listeners are loopback-only; connection from another LAN device fails. Review local competing-process risks and fixed-hop validation.
4. Windows secret storage passes positive and refusal tests. The POSIX fixture store is not substituted for it.
5. The owner reviews registration texts and application parameters before Production registration. No real credentials or linking are enabled by this document.
6. The owner completes linking and SCA. A phone redirect to localhost points at the phone, not the laptop. Confirm the bank/browser handoff returns to the Windows browser before starting.
7. Remove only this setup's exact certificate from CurrentUser My/Root when no longer needed. Never bulk-delete certificates. Verify listener closure and review residual data and backup exposure.

## References for further verification

- https://learn.microsoft.com/en-us/powershell/module/pki/new-selfsignedcertificate
- https://learn.microsoft.com/en-us/powershell/module/pki/export-certificate
- https://learn.microsoft.com/en-us/powershell/module/pki/import-certificate
- https://github.com/FiloSottile/mkcert
- https://enablebanking.com/docs/api/reference/

The references identify primitives and upstream guidance. They are not evidence that the full laptop flow or an Enable Banking redirect has been accepted or tested.

## OAuth URL exception

The provider authorization redirect necessarily carries transient state and code parameters in the browser callback URL. This is the sole protocol-required exception to the ban on placing these values in URLs. Do not copy, retain, publish, log or reuse that callback URL. The relay must consume it privately and return only a constant page, never links carrying those parameters. Review browser-history and local observation exposure in the real Windows flow.
