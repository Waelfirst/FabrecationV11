# Steel Structure Project Module - Complete Structure

## Directory Structure

```
steel_structure_project/
│
├── __init__.py                                 # Module initialization
├── __manifest__.py                             # Module manifest with dependencies
├── README.md                                   # Complete documentation
│
├── models/                                     # Business logic models
│   ├── __init__.py                            # Models initialization
│   ├── steel_project.py                       # Main project model
│   ├── steel_project_product.py               # Products within projects
│   ├── steel_project_components.py            # Component definitions
│   ├── steel_product_part.py                  # Individual parts with materials
│   ├── steel_production_stage.py              # Production workflow stages
│   ├── steel_project_evaluation.py            # Cost evaluation and quoting
│   ├── steel_project_operation.py             # Actual operation tracking
│   ├── steel_operation_stage.py               # Stage-level operation tracking
│   └── steel_actual_material.py               # Actual material consumption
│
├── views/                                      # UI definitions
│   ├── steel_project_views.xml                # Project views (form, tree, search)
│   ├── steel_project_product_views.xml        # Product views
│   ├── steel_project_components_views.xml     # Component views with tabs
│   ├── steel_project_evaluation_views.xml     # Evaluation views with cost breakdown
│   ├── steel_project_operation_views.xml      # Operation views (form, tree, kanban)
│   └── menu_views.xml                         # Main menu structure
│
├── security/                                   # Access control
│   └── ir.model.access.csv                    # Model access rights
│
└── demo/                                       # Sample data
    └── demo_data.xml                          # Complete demo dataset
```

## Model Relationships

```
steel.project (Main Project)
│
├──> steel.project.product (Products in Project)
│    │
│    └──> steel.project.components (Component Definition)
│         │
│         ├──> steel.product.part (Parts with Materials)
│         │    ├── material_id → product.product
│         │    └── Fields: quantity, unit_cost, total_cost
│         │
│         └──> steel.production.stage (Production Stages)
│              ├── worker_ids → hr.employee (Many2many)
│              ├── machine_ids → maintenance.equipment (Many2many)
│              └── Fields: required_time, hourly_rate, estimated_labor_cost
│
├──> steel.project.evaluation (Cost Evaluation)
│    ├── Computed: total_material_cost (from parts)
│    ├── Computed: total_labor_cost (from stages)
│    ├── Computed: total_estimated_cost
│    ├── Computed: overhead_cost
│    ├── Computed: profit_amount
│    └── Computed: final_quote
│
└──> steel.project.operation (Actual Operations)
     ├──> steel.operation.stage (Stage Tracking)
     │    ├── stage_id → steel.production.stage
     │    ├── Fields: estimated_time vs actual_time
     │    ├── Computed: time_variance, cost_variance
     │    └── State: pending → in_progress → completed
     │
     └──> steel.actual.material (Material Consumption)
          ├── material_id → product.product
          ├── part_id → steel.product.part
          └── Fields: quantity_used, unit_cost, total_cost
```

## Menu Structure

```
Steel Structure (Root Menu)
│
├── Projects
│   └── Action: action_steel_project
│       └── Views: tree, form
│
├── Project Components
│   └── Action: action_steel_project_components
│       └── Views: tree, form (with tabs: Parts, Stages)
│
├── Project Evaluation
│   └── Action: action_steel_project_evaluation
│       └── Views: tree, form (with tabs: Material Cost, Labor Cost)
│
├── Actual Operation
│   └── Action: action_steel_project_operation
│       └── Views: tree, kanban, form (with tabs: Stages, Materials)
│
└── Configuration
    └── Products
        └── Action: action_steel_project_product
```

## Key Fields by Model

### steel.project
- name, customer_id, start_date, end_date
- project_specs (text)
- product_ids (one2many)
- state: draft | in_progress | done | cancelled

### steel.project.product
- name, project_id, quantity, weight, dimensions
- component_ids (one2many)
- Auto-creates component on create

### steel.project.components
- project_id, product_id
- part_ids (one2many) - Product Parts
- stage_ids (one2many) - Production Stages

### steel.product.part
- part_name, material_id, quantity
- unit_cost (from material), total_cost (computed)
- current_stage_id (for tracking), is_completed

### steel.production.stage
- stage_name, required_time, hourly_rate
- worker_ids (many2many to hr.employee)
- machine_ids (many2many to maintenance.equipment)
- estimated_labor_cost (computed)

### steel.project.evaluation
- project_id
- total_material_cost (computed from all parts)
- total_labor_cost (computed from all stages)
- total_estimated_cost (material + labor)
- overhead_percentage, overhead_cost (computed)
- profit_margin_percentage, profit_amount (computed)
- final_quote (computed: cost + overhead + profit)

### steel.project.operation
- project_id, product_id, component_id
- stage_operation_ids (one2many)
- actual_material_ids (one2many)
- total_actual_time, total_actual_cost (computed)
- progress_percentage (computed)
- state: not_started | in_progress | completed

### steel.operation.stage
- operation_id, stage_id
- estimated_time, actual_time, time_variance (computed)
- estimated_cost, actual_labor_cost (computed), cost_variance (computed)
- start_date, end_date
- state: pending | in_progress | completed

### steel.actual.material
- operation_id, material_id, part_id
- quantity_used, unit_cost, total_cost (computed)
- usage_date

## Computed Field Summary

All costs are auto-calculated:

1. **Part Level**: `total_cost = quantity × unit_cost`
2. **Stage Level**: `estimated_labor_cost = required_time × hourly_rate`
3. **Evaluation Level**:
   - `total_material_cost = Σ(all part costs)`
   - `total_labor_cost = Σ(all stage costs)`
   - `total_estimated_cost = material + labor`
   - `overhead_cost = estimated × overhead_%`
   - `profit_amount = (estimated + overhead) × profit_%`
   - `final_quote = estimated + overhead + profit`
4. **Operation Level**:
   - `actual_labor_cost = actual_time × hourly_rate`
   - `time_variance = actual_time - estimated_time`
   - `cost_variance = actual_cost - estimated_cost`
   - `total_actual_cost = Σ(labor) + Σ(materials)`
   - `progress_% = completed_parts / total_parts × 100`

## Access Rights (ir.model.access.csv)

For each of the 9 models:
- **User Access** (base.group_user): Read, Write, Create (no delete)
- **Manager Access** (base.group_system): Full CRUD access

Total: 18 access rules

## Demo Data Includes

- 2 Customers (Construction companies)
- 4 Materials (Steel beams, plates, columns, welding rods)
- 3 Employees (Welder, Fabricator, Operator)
- 3 Equipment (Welding machine, Cutting machine, Press brake)
- 2 Projects (Warehouse, Factory extension)
- 3 Products across projects
- Multiple Parts per product (columns, beams, plates)
- Multiple Production Stages (Cutting, Welding, Finishing)
- 1 Evaluation with calculated costs
- 1 Active Operation with actual materials

## Installation Checklist

✅ All 9 models created with proper relationships
✅ All computed fields with dependencies defined
✅ Form, Tree, Search, and Kanban views created
✅ Menu structure with 5 main items
✅ Access rights for User and Manager groups
✅ Comprehensive demo data
✅ Auto-creation triggers (products → components)
✅ Workflow states and action buttons
✅ Many2many relations properly defined
✅ Currency fields for all monetary values
✅ Proper indexing and ordering

## Features Checklist

✅ Project lifecycle management
✅ Multi-product projects
✅ Component part breakdown
✅ Material cost tracking
✅ Production stage definition
✅ Worker and machine assignment
✅ Automatic cost calculations
✅ Cost evaluation with markup
✅ Actual operation tracking
✅ Time variance analysis
✅ Material consumption tracking
✅ Progress monitoring
✅ Status workflows
✅ Filters and grouping
✅ Mobile-friendly kanban view

## Next Steps for Users

1. Install module in Odoo 17
2. Review demo data to understand structure
3. Create your own projects
4. Define materials in Product module
5. Set up employees in HR module
6. Configure equipment in Maintenance module
7. Start tracking real projects!

---

**Module is production-ready for Odoo 17** ✅