/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Shopfloor Grid Widget
 * Displays production stages as squares with draggable work order cards
 */
class ShopfloorGridWidget extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            stages: [],
            workOrders: [],
            selectedCards: new Set(),
            draggedCard: null,
            searchTerm: "",
            filterState: "all",
            isLoading: true,
        });

        onMounted(() => {
            this.loadShopfloorData();
            this.setupDragAndDrop();
        });
    }

    /**
     * Load shopfloor data from backend
     */
    async loadShopfloorData() {
        this.state.isLoading = true;
        try {
            const operationId = this.props.record.resId;
            const result = await this.orm.call(
                "steel.project.operation",
                "get_shopfloor_data",
                [operationId]
            );

            this.state.stages = result.stages || [];
            this.state.workOrders = result.work_orders || [];
            this.state.isLoading = false;

            // Re-setup drag and drop after data loads
            setTimeout(() => this.setupDragAndDrop(), 100);
        } catch (error) {
            this.notification.add("Failed to load shopfloor data", {
                type: "danger",
            });
            this.state.isLoading = false;
        }
    }

    /**
     * Setup drag and drop functionality
     */
    setupDragAndDrop() {
        // Add drag listeners to all part cards
        const cards = document.querySelectorAll(".part-card");
        cards.forEach((card) => {
            card.setAttribute("draggable", "true");

            card.addEventListener("dragstart", (e) => {
                card.classList.add("dragging");
                this.state.draggedCard = parseInt(card.dataset.woId);
                e.dataTransfer.effectAllowed = "move";
                e.dataTransfer.setData("text/html", card.innerHTML);
            });

            card.addEventListener("dragend", (e) => {
                card.classList.remove("dragging");
                this.state.draggedCard = null;
            });
        });

        // Add drop listeners to all stages
        const stages = document.querySelectorAll(".stage-square");
        stages.forEach((stage) => {
            stage.addEventListener("dragover", (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = "move";
                stage.classList.add("drag-over");
            });

            stage.addEventListener("dragleave", (e) => {
                stage.classList.remove("drag-over");
            });

            stage.addEventListener("drop", async (e) => {
                e.preventDefault();
                stage.classList.remove("drag-over");

                const targetStageId = parseInt(stage.dataset.stageId);
                await this.moveCardToStage(this.state.draggedCard, targetStageId);
            });
        });
    }

    /**
     * Move work order card to new stage
     */
    async moveCardToStage(workOrderId, targetStageId) {
        if (!workOrderId || !targetStageId) return;

        try {
            // If multiple cards selected, use bulk move
            if (this.state.selectedCards.size > 1 && this.state.selectedCards.has(workOrderId)) {
                await this.bulkMoveCards(Array.from(this.state.selectedCards), targetStageId);
            } else {
                // Single card move
                await this.orm.call(
                    "steel.work.order",
                    "action_move_to_stage",
                    [workOrderId, targetStageId]
                );

                this.notification.add("Part moved successfully", {
                    type: "success",
                });
            }

            // Reload data
            await this.loadShopfloorData();

        } catch (error) {
            this.notification.add("Failed to move part: " + error.message, {
                type: "danger",
            });
        }
    }

    /**
     * Bulk move multiple cards
     */
    async bulkMoveCards(workOrderIds, targetStageId) {
        // Open bulk move wizard
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Move Selected Parts",
            res_model: "steel.work.order.bulk.move.wizard",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_work_order_ids: [[6, 0, workOrderIds]],
                default_target_stage_id: targetStageId,
            },
        });
    }

    /**
     * Move selected cards between Operations by dropping onto an Operation column
     * Requires stage columns to carry a data-operation-id in template
     */
    async moveCardsToOperation(workOrderIds, targetOperationId) {
        if (!workOrderIds?.length || !targetOperationId) return;
        await this.action.doAction({
            type: "ir.actions.act_window",
            name: "Move Selected Parts",
            res_model: "steel.work.order.bulk.move.wizard",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_work_order_ids: [[6, 0, workOrderIds]],
                default_target_operation_id: targetOperationId,
            },
        });
    }

    /**
     * Toggle card selection
     */
    toggleCardSelection(workOrderId, event) {
        if (event.ctrlKey || event.metaKey) {
            if (this.state.selectedCards.has(workOrderId)) {
                this.state.selectedCards.delete(workOrderId);
            } else {
                this.state.selectedCards.add(workOrderId);
            }
        } else {
            this.state.selectedCards.clear();
            this.state.selectedCards.add(workOrderId);
        }
    }

    /**
     * Open quick edit dialog for a card
     */
    async openQuickEdit(workOrderId) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "steel.work.order",
            res_id: workOrderId,
            views: [[false, "form"]],
            view_mode: "form",
            target: "new",
        });

        // Reload after closing
        setTimeout(() => this.loadShopfloorData(), 500);
    }

    /**
     * Filter work orders by search term
     */
    handleSearch(event) {
        this.state.searchTerm = event.target.value.toLowerCase();
    }

    /**
     * Filter work orders by state
     */
    handleFilterState(filterState) {
        this.state.filterState = filterState;
    }

    /**
     * Check if work order matches current filters
     */
    matchesFilters(workOrder) {
        // Search filter
        if (this.state.searchTerm) {
            const searchIn = `${workOrder.part_name} ${workOrder.material}`.toLowerCase();
            if (!searchIn.includes(this.state.searchTerm)) {
                return false;
            }
        }

        // State filter
        if (this.state.filterState !== "all") {
            if (workOrder.state !== this.state.filterState) {
                return false;
            }
        }

        return true;
    }

    /**
     * Get filtered work orders for a stage
     */
    getFilteredWorkOrders(stage) {
        return stage.work_orders.filter(wo => this.matchesFilters(wo));
    }

    /**
     * Get CSS class for work order state
     */
    getStateClass(state) {
        return `state-${state}`;
    }

    /**
     * Get badge color for state
     */
    getStateBadgeClass(state) {
        const classes = {
            'done': 'bg-success',
            'in_progress': 'bg-warning text-dark',
            'blocked': 'bg-danger',
            'ready': 'bg-secondary',
        };
        return classes[state] || 'bg-secondary';
    }

    /**
     * Format time display
     */
    formatTime(hours) {
        const h = Math.floor(hours);
        const m = Math.round((hours - h) * 60);
        return `${h}h ${m}m`;
    }

    /**
     * Format currency display
     */
    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
        }).format(amount);
    }
}

ShopfloorGridWidget.template = "steel_structure_project.ShopfloorGridWidget";

registry.category("fields").add("shopfloor_grid_widget", {
    component: ShopfloorGridWidget,
});

export default ShopfloorGridWidget;