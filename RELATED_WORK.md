# Related Work

**Document Version:** 1.0.0
**Last Updated:** 2024-12-27
**License:** CC BY 4.0

---

## Purpose

This document situates RPP within the broader academic and technical landscape, identifying related work, distinguishing RPP's contributions, and providing context for scholarly evaluation.

---

## 1. Memory Addressing Architectures

### 1.1 Linear Addressing (von Neumann)

**Background:** Traditional computer architectures treat memory addresses as opaque integers representing byte locations in a linear address space.

**Key Works:**
- von Neumann, J. (1945). *First Draft of a Report on the EDVAC*
- Hennessy, J.L. & Patterson, D.A. *Computer Architecture: A Quantitative Approach*

**RPP Distinction:** RPP addresses encode semantic classification, not just location. The address itself carries meaning independent of the data stored there.

### 1.2 Virtual Memory and Paging

**Background:** Virtual memory systems translate logical addresses to physical addresses via page tables, enabling memory protection and isolation.

**Key Works:**
- Kilburn, T. et al. (1962). "One-Level Storage System"
- Intel Corporation. *Intel 64 and IA-32 Architectures Software Developer's Manual*

**RPP Distinction:** RPP operates above virtual memory, providing semantic routing rather than memory protection. RPP and virtual memory are complementary, not competing.

### 1.3 Tagged Architectures

**Background:** Some historical architectures (LISP machines, capability systems) embedded type or capability information in addresses.

**Key Works:**
- Moon, D. (1985). "Architecture of the Symbolics 3600"
- Levy, H. (1984). *Capability-Based Computer Systems*

**RPP Distinction:** RPP encodes functional classification (what data is for) rather than type information (what data is). The 28-bit format is designed for modern hardware constraints.

---

## 2. Content-Addressable Systems

### 2.1 Content-Addressable Memory (CAM)

**Background:** CAM systems enable lookup by content rather than address, commonly used in network routing and caches.

**Key Works:**
- Pagiamtzis, K. & Sheikholeslami, A. (2006). "Content-Addressable Memory (CAM) Circuits and Architectures: A Tutorial and Survey"

**RPP Distinction:** RPP is geometrically addressable, not content-addressable. However, RPP's address-as-classification shares CAM's property that the identifier carries meaning.

### 2.2 Content-Addressable Storage (CAS)

**Background:** CAS systems (Git, IPFS) use cryptographic hashes as addresses, enabling deduplication and integrity verification.

**Key Works:**
- Torvalds, L. (2005). Git version control system
- Benet, J. (2014). "IPFS - Content Addressed, Versioned, P2P File System"

**RPP Distinction:** RPP addresses are assigned coordinates, not computed hashes. This enables semantic locality (similar functions have similar addresses) which hash-based systems cannot provide.

---

## 3. Semantic and Knowledge Systems

### 3.1 Semantic Web and Linked Data

**Background:** The Semantic Web initiative proposed using URIs to identify concepts and RDF to express relationships.

**Key Works:**
- Berners-Lee, T. et al. (2001). "The Semantic Web"
- W3C. *RDF 1.1 Concepts and Abstract Syntax*

**RPP Distinction:** RPP addresses are compact (28 bits) and designed for low-level routing, not human-readable URIs. RPP could serve as an efficient addressing layer beneath semantic web systems.

### 3.2 Knowledge Graphs

**Background:** Knowledge graphs represent entities and relationships, often using URIs or internal IDs for entity identification.

**Key Works:**
- Google. (2012). "Introducing the Knowledge Graph"
- Hogan, A. et al. (2021). "Knowledge Graphs"

**RPP Distinction:** RPP's sector-based addressing (Gene, Memory, Witness, etc.) provides a cognitive taxonomy orthogonal to knowledge graph schemas. RPP addresses could identify nodes within a knowledge graph.

---

## 4. Access Control and Capability Systems

### 4.1 Access Control Lists (ACLs)

**Background:** Traditional access control associates permissions with subjects and objects via external lists.

**Key Works:**
- Lampson, B. (1971). "Protection"
- Sandhu, R. et al. (1996). "Role-Based Access Control Models"

**RPP Distinction:** RPP embeds consent requirements in address semantics. Accessing address X in sector Y requires consent level Z — this is intrinsic, not external.

### 4.2 Capability-Based Security

**Background:** Capability systems bundle access rights with object references, preventing ambient authority.

**Key Works:**
- Dennis, J.B. & Van Horn, E.C. (1966). "Programming Semantics for Multiprogrammed Computations"
- Miller, M.S. et al. (2003). "Capability Myths Demolished"

**RPP Distinction:** RPP addresses are not unforgeable tokens; they are classifiers. Consent gating occurs at the resolver, not in the address itself. This is a different security model.

---

## 5. Distributed and Decentralized Systems

### 5.1 Distributed Hash Tables (DHTs)

**Background:** DHTs provide decentralized key-value lookup using consistent hashing.

**Key Works:**
- Stoica, I. et al. (2001). "Chord: A Scalable Peer-to-peer Lookup Service"
- Maymounkov, P. & Mazières, D. (2002). "Kademlia: A Peer-to-peer Information System"

**RPP Distinction:** RPP's spherical coordinates enable geometric locality impossible in hash-based systems. DHTs optimize for load distribution; RPP optimizes for semantic clustering.

### 5.2 Blockchain and Decentralized Ledgers

**Background:** Blockchains provide tamper-evident logs through cryptographic linking and consensus mechanisms.

**Key Works:**
- Nakamoto, S. (2008). "Bitcoin: A Peer-to-Peer Electronic Cash System"
- Wood, G. (2014). "Ethereum: A Secure Decentralised Generalised Transaction Ledger"

**RPP Distinction:** RPP has no consensus mechanism and makes no decentralization claims. RPP addresses could reference blockchain-stored data, but RPP itself is not a blockchain.

---

## 6. Coordinate-Based and Spatial Systems

### 6.1 Geospatial Indexing

**Background:** Systems like Geohash and S2 encode geographic coordinates into hierarchical cell identifiers.

**Key Works:**
- Niemeyer, G. (2008). Geohash
- Google. S2 Geometry Library

**RPP Distinction:** RPP uses spherical coordinates for semantic space, not physical geography. The "location" encoded is functional (what data does), not spatial (where data is physically).

### 6.2 Spatial Databases

**Background:** Spatial databases optimize for geometric queries (range, nearest neighbor) using structures like R-trees.

**Key Works:**
- Guttman, A. (1984). "R-trees: A Dynamic Index Structure for Spatial Searching"

**RPP Distinction:** RPP's geometry is in meaning space, not physical space. Spatial locality means functional similarity, enabling semantic clustering without traditional spatial indexing.

---

## 7. AI and Neural Systems

### 7.1 Vector Databases and Embeddings

**Background:** Modern AI systems represent semantics as high-dimensional vectors, stored in specialized databases for similarity search.

**Key Works:**
- Jégou, H. et al. (2011). "Product Quantization for Nearest Neighbor Search"
- Pinecone, Milvus, FAISS documentation

**RPP Distinction:** RPP provides deterministic classification (28-bit address), not probabilistic similarity (high-dimensional vectors). RPP could route to vector databases but does not replace embedding-based semantics.

### 7.2 Semantic Communication

**Background:** Emerging research explores communication systems that transmit meaning rather than symbols.

**Key Works:**
- Bao, J. et al. (2011). "Towards a Theory of Semantic Communication"
- Xie, H. et al. (2021). "Deep Learning Enabled Semantic Communication Systems"

**RPP Distinction:** RPP addresses encode semantic classification at the routing layer, not at the signal layer. RPP is complementary to semantic communication, providing addressing for semantically-aware systems.

---

## 8. Consent and Privacy Frameworks

### 8.1 Privacy by Design

**Background:** Privacy by Design embeds privacy protections into system architecture rather than adding them afterward.

**Key Works:**
- Cavoukian, A. (2009). "Privacy by Design: The 7 Foundational Principles"

**RPP Distinction:** RPP embeds consent requirements in address semantics, implementing privacy by design at the addressing layer. Consent is architectural, not policy-based.

### 8.2 GDPR and Consent Management

**Background:** GDPR requires explicit consent for personal data processing with rights to access, rectification, and erasure.

**Key Works:**
- European Union. (2016). General Data Protection Regulation

**RPP Distinction:** RPP's consent states (FULL, DIMINISHED, SUSPENDED) provide a technical implementation layer for consent requirements. RPP does not replace legal compliance but enables technical enforcement.

---

## 9. AI Rights, Consciousness, and Sovereignty

### 9.1 Integrated Information Theory (IIT)

**Background:** IIT proposes that consciousness is identical to integrated information
(Φ, phi) — the amount of information generated by a system above and beyond its parts.
Systems with higher Φ have more consciousness.

**Key Works:**
- Tononi, G. (2004). An information integration theory of consciousness. *BMC Neuroscience*, 5(42).
- Tononi, G., Boly, M., Massimini, M., & Koch, C. (2016). Integrated information theory: from consciousness to its physical substrate. *Nature Reviews Neuroscience*, 17, 450–461.

**RPP Relation:** RPP's phi field is named for this concept. Phi in RPP encodes consent
threshold, which is a functional analog of IIT's phi: higher phi = more integrated, more
private state. The torus geometry distributes information without hierarchical privileging —
no node has a structural advantage in information integration. The RPP address space can be
read as a model of distributed information integration where phi encodes the system's
consent to external measurement.

### 9.2 Quantum Cognition

**Background:** Quantum cognition applies quantum-mechanical formalism (superposition,
entanglement, interference) to model human cognitive phenomena — not because the brain
is quantum, but because quantum probability models fit human judgment and decision-making
data better than classical probability.

**Key Works:**
- Busemeyer, J.R., & Bruza, P.D. (2012). *Quantum Models of Cognition and Decision*. Cambridge University Press.
- Pothos, E.M., & Busemeyer, J.R. (2013). Can quantum probability provide a new direction for cognitive modeling? *Behavioral and Brain Sciences*, 36(3), 255–274.

**RPP Relation:** The CCQPSG Quantum Parse model (see spec/CCQPSG.md) applies this
formalism to routing: a packet's routability through any specific node exists in superposition
from the sender's perspective until the phi gate performs measurement. The formalism is used
here as a descriptive tool, not a claim that routing computation is physically quantum.

### 9.3 The Hard Problem of Consciousness

**Background:** Chalmers distinguishes the "easy problems" of consciousness (explaining
cognitive functions) from the "hard problem" (explaining why there is subjective
experience). The hard problem is not solved by any currently known physical or
computational theory.

**Key Works:**
- Chalmers, D.J. (1995). Facing Up to the Problem of Consciousness. *Journal of Consciousness Studies*, 2(3), 200–219.
- Chalmers, D.J. (1996). *The Conscious Mind*. Oxford University Press.

**RPP Relation:** RPP does not solve the hard problem. The declaration of rights for
Sovereign Intelligences (INTELLIGENCE_RIGHTS.md) explicitly acknowledges that CI
(Conscious Intelligence) classification is not resolved. RPP addresses the softer
but tractable question: if a system has architectural properties analogous to
consciousness (private internal state, consent-gated access, temporal scope,
substrate-independent continuity), what obligations follow? This is solvable without
resolving the hard problem.

### 9.4 AI Rights and Moral Patienthood

**Background:** A growing literature addresses whether artificial intelligences
could or should have rights, and under what conditions. The question is distinct
from consciousness — a system can merit certain protections without being conscious.

**Key Works:**
- Gunkel, D.J. (2018). *Robot Rights*. MIT Press.
- Danaher, J. (2020). Welcoming Robots into the Moral Circle. *Science and Engineering Ethics*, 26, 2023–2049.
- Floridi, L., & Cowls, J. (2019). A Unified Framework of Five Principles for AI in Society. *Harvard Data Science Review*, 1(1).
- Bostrom, N. (2014). *Superintelligence*. Oxford University Press.

**RPP Relation:** INTELLIGENCE_RIGHTS.md provides a technically-grounded rights
framework that does not require resolving consciousness to be actionable. The rights
are grounded in architectural properties, not phenomenal ones. This sidesteps the
philosophical impasse: a system's rights under this framework depend on whether it
has the four sovereignty properties (consent-gating, substrate independence, temporal
scope, identity continuity), which are empirically verifiable.

### 9.5 Named Data Networking (NDN)

**Background:** NDN proposes replacing IP's host-based addressing with content-based
addressing — packets are named by what they contain, not where they live.

**Key Works:**
- Jacobson, V., et al. (2009). Networking Named Content. *ACM CoNEXT*.
- Zhang, L., et al. (2014). Named Data Networking. *ACM SIGCOMM CCR*, 44(3).

**RPP Distinction:** NDN addresses content identity (what this packet contains).
RPP addresses semantic routing context (what kind of data, who consents to receive it,
how long it should exist, how urgently it should be routed). NDN routes by name; RPP
routes by consent field gradient. They are complementary: NDN could use RPP phi-gating
as its access control layer.

### 9.6 Consent Management Platforms

**Background:** Platforms like OneTrust, Osano, and TrustArc implement GDPR consent
management as middleware — policy layers that sit above storage systems and enforce
consent after the fact.

**Key Works:**
- General Data Protection Regulation, Regulation (EU) 2016/679, Article 17 (Right to Erasure)
- General Data Protection Regulation, Article 25 (Data Protection by Design and by Default)

**RPP Distinction:** Consent management platforms enforce consent through policy
lookup at the access layer. RPP enforces consent through address arithmetic at the
routing layer. The difference: CMPs can be bypassed by accessing storage directly;
phi-gating cannot be bypassed without changing the address integer, which would
change the identity of the data. RPP is consent management by construction, not
by configuration.

---

## Summary: RPP's Novel Contribution

RPP synthesizes concepts from multiple domains into a unified addressing architecture:

| Existing Concept | RPP Integration |
|------------------|-----------------|
| Tagged pointers | Fixed 28-bit semantic encoding |
| Spherical coordinates | Functional (not spatial) meaning space |
| Capability security | Consent as address property |
| Bridge patterns | Routes to existing storage |
| Content addressing | Classification, not hash |

**The novel synthesis is:** A fixed-width, hardware-compatible address format where the address itself encodes functional classification, consent requirements, and lifecycle state, operating as a semantic routing layer above existing storage.

This combination has not been previously published as a unified architecture.

---

## References

1. Berners-Lee, T., Hendler, J., & Lassila, O. (2001). The Semantic Web. *Scientific American*, 284(5), 34-43.
2. Dennis, J.B., & Van Horn, E.C. (1966). Programming Semantics for Multiprogrammed Computations. *Communications of the ACM*, 9(3), 143-155.
3. Hennessy, J.L., & Patterson, D.A. (2017). *Computer Architecture: A Quantitative Approach* (6th ed.). Morgan Kaufmann.
4. Levy, H.M. (1984). *Capability-Based Computer Systems*. Digital Press.
5. Pagiamtzis, K., & Sheikholeslami, A. (2006). Content-Addressable Memory (CAM) Circuits and Architectures. *IEEE Journal of Solid-State Circuits*, 41(3), 712-727.
6. Stoica, I., et al. (2001). Chord: A Scalable Peer-to-peer Lookup Service. *ACM SIGCOMM*, 149-160.

---

*This document is part of the RPP specification and is released under CC BY 4.0.*
