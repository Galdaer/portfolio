# TODO - Immediate Domain Expertise Tasks

**Last Updated**: 2025-08-06  
**Purpose**: Healthcare domain tasks requiring human expertise while coding agent handles database-first refactoring

---

## 🎯 PRIORITY 1: Fix PHI Detection Testing

**Issue**: Our PHI detector ignores @example.com, but synthetic data uses it, making PHI testing ineffective
**Location**: `scripts/generate_synthetic_healthcare_data.py`

```python
# Current Problem: PHI detector skips @example.com emails
# Solution: Generate realistic email domains that WILL be checked

- [ ] Replace @example.com with realistic domains:
    EMAIL_DOMAINS = [
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
        'aol.com', 'icloud.com', 'protonmail.com', 'fastmail.com',
        'healthcare-system.org', 'clinic-network.com'
    ]
    
- [ ] Create PHI-triggering email patterns:
    - john.smith.diabetes@gmail.com ❌ (contains condition)
    - patient12345@yahoo.com ❌ (contains "patient")
    - jsmith1950@gmail.com ❌ (contains birth year)
    - john.smith@gmail.com ✅ (should pass)
    
- [ ] Test comprehensive PHI patterns:
    - Generate 1000 emails with varying PHI risk levels
    - Document detection rates for each pattern type
    - Ensure 95%+ detection of actual PHI patterns
```

---

## 🎯 PRIORITY 2: Universal Insurance Calculator

**Goal**: "Onboarding new clients is as simple as possible" - handle ANY insurance type
**Location**: Create `core/insurance/universal_calculator.py`

```python
# Build flexible system that adapts to any insurance structure

- [ ] Create universal insurance data model:
    class InsurancePlan:
        plan_type: str  # PPO, HMO, EPO, POS, HDHP, Medicaid, Medicare, etc.
        
        # Deductibles (individual vs family)
        deductible_individual: Decimal
        deductible_family: Decimal
        deductible_met_individual: Decimal
        deductible_met_family: Decimal
        
        # Out of pocket maximums
        oop_max_individual: Decimal
        oop_max_family: Decimal
        oop_met_individual: Decimal
        oop_met_family: Decimal
        
        # Variable cost structures
        copay_rules: Dict[str, Decimal]  # {"primary": 25, "specialist": 50}
        coinsurance_rules: Dict[str, float]  # {"in_network": 0.20, "out_network": 0.40}
        
        # Special rules
        prior_auth_required: List[str]  # CPT codes needing auth
        referral_required: bool
        network_restrictions: Dict[str, Any]

- [ ] Implement adaptive calculation engine:
    def calculate_patient_cost(
        plan: InsurancePlan,
        services: List[MedicalService],
        provider_network_status: str
    ) -> CostBreakdown:
        """
        Returns exact cost with confidence level
        Shows: deductible progress, coinsurance applied, final cost
        """

- [ ] Build client onboarding templates:
    # Templates for common insurance types
    insurance_templates/
        ├── commercial/
        │   ├── bcbs_ppo.yaml
        │   ├── united_hmo.yaml
        │   └── aetna_hdhp.yaml
        ├── government/
        │   ├── medicare_part_b.yaml
        │   ├── medicaid_standard.yaml
        │   └── tricare_prime.yaml
        └── custom/
            └── client_specific.yaml  # Easy customization

- [ ] Create insurance discovery system:
    # Auto-detect insurance patterns from claims data
    def discover_insurance_rules(historical_claims: List[Claim]) -> InsurancePlan:
        """Learns insurance rules from actual claim processing"""
```

---

## 🎯 PRIORITY 3: Medical Reference Mirroring

**Goal**: Offline access to critical medical databases
**Location**: `scripts/mirror-medical-references.sh` and `core/medical_references/`

```bash
# Critical medical references to mirror locally

- [ ] Implement PubMed Central mirror:
    # Use PMC OAI-PMH for bulk downloads
    # Store in data/medical-references/pubmed/
    # ~35GB for open access subset
    
- [ ] Mirror ClinicalTrials.gov:
    # Use their bulk data export API
    # Store in data/medical-references/clinical-trials/
    # ~5GB compressed
    
- [ ] Cache FDA drug database:
    # Download FDA Orange Book, NDC directory
    # Store in data/medical-references/fda/
    # ~2GB total
    
- [ ] DSM-5-TR reference integration:
    # Note: Copyrighted - need license
    # Create interface for manual import if client has license
    # Store in data/medical-references/dsm/ (if licensed)
    
- [ ] ICD-10-CM/PCS codes:  # This is what you were thinking of!
    # Download from CMS.gov (public domain)
    # Store in data/medical-references/icd10/
    # ~50MB for complete codeset
    
- [ ] CPT codes structure:
    # Note: Proprietary (AMA owned)
    # Create import interface for clients with licenses
    # Store in data/medical-references/cpt/ (if licensed)

- [ ] Create unified search interface:
    class MedicalReferenceSearch:
        def search_all_sources(query: str, sources: List[str]) -> Results:
            # Search local mirrors first
            # Fall back to online if needed
            # Cache results for offline use
```

**Implementation approach:**
```python
# Priority order for immediate implementation
1. ICD-10 codes (free, essential for billing)
2. FDA drug database (free, critical for safety)
3. PubMed abstracts (free, research backbone)
4. Clinical trials (free, evidence base)
5. DSM-5-TR interface (paid, client provides)
6. CPT interface (paid, client provides)
```

---

## ✅ WHAT THE CODING AGENT IS DOING

Per `CODING_AGENT_ALIGNMENT_PROMPT.md`:
- **Database-first refactoring**: Removing ALL synthetic file fallbacks
- **Basic MCP offline structure**: Creating initial `scripts/mirror-mcp-websites.sh`
- **Instruction cleanup**: Removing duplication across agent files

**Note**: The coding agent will create basic mirroring structure, but YOU need to implement the actual medical database downloads since they require domain knowledge of which resources are critical.

---

## 🚀 START HERE

```bash
# 1. Fix email generation for PHI testing
code scripts/generate_synthetic_healthcare_data.py

# 2. Build universal insurance system
mkdir -p core/insurance
touch core/insurance/__init__.py
touch core/insurance/universal_calculator.py
mkdir -p insurance_templates/{commercial,government,custom}
code core/insurance/

# 3. Implement medical reference mirroring
mkdir -p data/medical-references/{icd10,fda,pubmed,clinical-trials}
code scripts/mirror-medical-references.sh

# 4. Start with ICD-10 (it's free and essential)
wget https://www.cms.gov/files/zip/2024-icd-10-cm-codes-file.zip
wget https://www.cms.gov/files/zip/2024-icd-10-pcs-codes-file.zip
```

---

## 📊 SUCCESS METRICS

**PHI Detection**: 
- [ ] Zero @example.com emails in production data
- [ ] 95%+ detection rate on PHI-pattern emails
- [ ] <5% false positives on legitimate emails

**Insurance System**:
- [ ] Handles 10+ different insurance plan types
- [ ] Accurate to penny for known fee schedules
- [ ] New client onboarding < 1 hour
- [ ] Deductible tracking shows exact progress

**Medical References**:
- [ ] ICD-10 codes searchable offline
- [ ] FDA drug database cached locally
- [ ] PubMed abstracts available offline
- [ ] Sub-second search across all sources

---

**Next Steps**: After these complete + coding agent finishes → Move to `FUTURE_TODO.md` for Phase 2 features