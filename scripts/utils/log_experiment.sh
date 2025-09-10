#!/bin/bash

# VGGT-Gaussian Splatting 실험 로그 자동화 스크립트

EXPERIMENT_LOG="/workspace/EXPERIMENT_LOG.md"

function add_experiment() {
    local exp_id=$1
    local name=$2
    local objective=$3
    local command=$4
    
    echo "" >> $EXPERIMENT_LOG
    echo "### **EXP-$exp_id: $name**" >> $EXPERIMENT_LOG
    echo "- **Date**: $(date +%Y-%m-%d)" >> $EXPERIMENT_LOG
    echo "- **Status**: 🔄 In Progress" >> $EXPERIMENT_LOG
    echo "- **Objective**: $objective" >> $EXPERIMENT_LOG
    echo "- **Command**: \`$command\`" >> $EXPERIMENT_LOG
    echo "- **Started**: $(date '+%Y-%m-%d %H:%M:%S')" >> $EXPERIMENT_LOG
    
    echo "✅ Experiment EXP-$exp_id added to log"
}

function complete_experiment() {
    local exp_id=$1
    local results=$2
    local vram=$3
    local time=$4
    
    # Update the experiment entry
    echo "- **Results**: $results" >> $EXPERIMENT_LOG
    echo "- **VRAM**: ${vram}GB" >> $EXPERIMENT_LOG  
    echo "- **Time**: ${time}min" >> $EXPERIMENT_LOG
    echo "- **Completed**: $(date '+%Y-%m-%d %H:%M:%S')" >> $EXPERIMENT_LOG
    echo "- **Status**: ✅ Complete" >> $EXPERIMENT_LOG
    
    echo "✅ Experiment EXP-$exp_id marked complete"
}

function fail_experiment() {
    local exp_id=$1
    local error=$2
    
    echo "- **Error**: $error" >> $EXPERIMENT_LOG
    echo "- **Status**: ❌ Failed" >> $EXPERIMENT_LOG
    echo "- **Failed**: $(date '+%Y-%m-%d %H:%M:%S')" >> $EXPERIMENT_LOG
    
    echo "❌ Experiment EXP-$exp_id marked failed"
}

function show_usage() {
    echo "Usage:"
    echo "  $0 add <exp_id> \"<name>\" \"<objective>\" \"<command>\""
    echo "  $0 complete <exp_id> \"<results>\" <vram_gb> <time_min>"
    echo "  $0 fail <exp_id> \"<error_message>\""
    echo ""
    echo "Examples:"
    echo "  $0 add 001 \"PLY Extraction\" \"Extract 50K model\" \"python export_ply.py\""
    echo "  $0 complete 001 \"2M Gaussians extracted\" 5.2 3"
    echo "  $0 fail 001 \"CUDA OOM error\""
}

# Main logic
case $1 in
    "add")
        if [ $# -eq 5 ]; then
            add_experiment "$2" "$3" "$4" "$5"
        else
            show_usage
        fi
        ;;
    "complete")
        if [ $# -eq 5 ]; then
            complete_experiment "$2" "$3" "$4" "$5"
        else
            show_usage
        fi
        ;;
    "fail")
        if [ $# -eq 3 ]; then
            fail_experiment "$2" "$3"
        else
            show_usage
        fi
        ;;
    *)
        show_usage
        ;;
esac