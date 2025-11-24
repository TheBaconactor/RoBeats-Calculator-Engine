-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:54 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_5 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_6 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_8 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_9 = require(game.ReplicatedStorage.Avatar.EquipmentUpgradeDatabase)
local v_u_10 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_11 = require(game.ReplicatedStorage.Avatar.GearStatsDescriptions)
local v_u_12 = require(game.ReplicatedStorage.Avatar.ElementalColor)
require(game.ReplicatedStorage.Shared.TextSizeCache)
require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_13 = require(game.ReplicatedStorage.Pets.PetUtils)
local v_u_19 = {
    ["display_stat_icon_for_sub_text"] = function(_, p14, p15, p16) --[[ Name: display_stat_icon_for_sub_text ]] --[[ Line: 363 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_12, (copy 3): v_u_3 ]]
        local v17 = p14:FindFirstChild("StatIcon")
        if v17 ~= nil then
            local v18 = v_u_4:gearstats_type_to_elemental_color(p15)
            if v18 ~= nil then
                v17.Position = UDim2.new(0, p14.TextBounds.X + p16, 0, 0)
                v17.Image = v_u_12:color_to_iconimage(v18)
                v17.Visible = true
                return;
            end;
            v17.Image = v_u_3:transparent_assetid()
            v17.Visible = false
        end;
    end
}
v_u_19.new = function(_, p_u_20, p_u_21) --[[ Name: new ]] --[[ Line: 20 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_19, (copy 3): v_u_4, (copy 4): v_u_2, (copy 5): v_u_9, (copy 6): v_u_10, (copy 7): v_u_11, (copy 8): v_u_8, (copy 9): v_u_5, (copy 10): v_u_6, (copy 11): v_u_7, (copy 12): v_u_3, (copy 13): v_u_13 ]]
    local v_u_22 = {}
    local v_u_23 = nil
    local v_u_24 = nil
    local v_u_25 = nil
    local v_u_26 = nil
    local v_u_27 = nil
    local v_u_28 = nil
    local v_u_29 = nil
    local v_u_30 = nil
    local v_u_31 = nil
    local v_u_32 = nil
    local v_u_33 = v_u_1:new()
    local v_u_34 = v_u_1:new()
    v_u_22.cons = function(_) --[[ Name: cons ]] --[[ Line: 33 ]]
        --[[ Upvalues: (ref 1): p_u_21, (copy 2): p_u_20, (ref 3): v_u_23, (ref 4): v_u_24, (ref 5): v_u_29, (ref 6): v_u_25, (ref 7): v_u_26, (ref 8): v_u_27, (ref 9): v_u_28, (ref 10): v_u_30, (ref 11): v_u_31, (ref 12): v_u_32, (copy 13): v_u_33, (ref 14): v_u_19, (ref 15): v_u_4, (copy 16): v_u_34 ]]
        if p_u_21 == nil then
            p_u_21 = p_u_20.SurfaceGui.Frame
        end;
        if p_u_21:FindFirstChild("IconSection") then
            v_u_23 = p_u_21.IconSection.Icon
        end;
        if p_u_21:FindFirstChild("NameDisplay") then
            v_u_24 = p_u_21.NameDisplay
        end;
        if p_u_21:FindFirstChild("BonusDisplay") then
            v_u_29 = p_u_21.BonusDisplay
        end;
        v_u_25 = p_u_21.StatDisplay1
        v_u_26 = p_u_21.StatDisplay2
        v_u_27 = p_u_21.StatDisplay3
        v_u_28 = p_u_21.StatDisplay4
        if p_u_21:FindFirstChild("SlotDisplay") then
            v_u_30 = p_u_21.SlotDisplay
        end;
        if p_u_21:FindFirstChild("SlotIcon") then
            v_u_31 = p_u_21.SlotIcon
        end;
        if p_u_21:FindFirstChild("StatPageDisplay") then
            v_u_32 = p_u_21.StatPageDisplay
        end;
        v_u_33:push_back_table_list({
            v_u_25,
            v_u_26,
            v_u_27,
            v_u_28
        })
        for v35 = 1, v_u_33:count() do
            v_u_19:display_stat_icon_for_sub_text(v_u_33:get(v35), v_u_4.Type.NoStat, 0)
        end;
        local function _(p36) --[[ Name: add_description_if_exists ]] --[[ Line: 67 ]]
            --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_34 ]]
            local v37 = p_u_21:FindFirstChild(p36)
            if v37 then
                v_u_34:push_back(v37)
            end;
        end;
        local v38 = p_u_21:FindFirstChild("StatDescription1")
        if v38 then
            v_u_34:push_back(v38)
        end;
        local v39 = p_u_21:FindFirstChild("StatDescription2")
        if v39 then
            v_u_34:push_back(v39)
        end;
        local v40 = p_u_21:FindFirstChild("StatDescription3")
        if v40 then
            v_u_34:push_back(v40)
        end;
        local v41 = p_u_21:FindFirstChild("StatDescription4")
        if v41 then
            v_u_34:push_back(v41)
        end;
    end;
    v_u_22.set_ui_elements = function(_, p42, p43, p44, p45, p46, p47, p48, p49) --[[ Name: set_ui_elements ]] --[[ Line: 79 ]]
        --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_23, (ref 3): v_u_24, (ref 4): v_u_25, (ref 5): v_u_26, (ref 6): v_u_27, (ref 7): v_u_28, (ref 8): v_u_29 ]]
        p_u_21 = p42
        v_u_23 = p43
        v_u_24 = p44
        v_u_25 = p45
        v_u_26 = p46
        v_u_27 = p47
        v_u_28 = p48
        v_u_29 = p49
    end;
    local function _(p50) --[[ Name: sort_stats_list ]] --[[ Line: 90 ]]
        --[[ Upvalues: (ref 1): v_u_4 ]]
        p50:sort(function(p51, p52) --[[ Line: 91 ]]
            --[[ Upvalues: (ref 1): v_u_4 ]]
            local v53 = v_u_4:gearstats_type_to_elemental_color(p51.Stat)
            local v54 = v_u_4:gearstats_type_to_elemental_color(p52.Stat)
            if v53 == nil or v54 == nil then
                if v53 == nil then
                    if v54 == nil then
                        return math.abs(p51.Value) - math.abs(p52.Value);
                    else
                        return false;
                    end;
                else
                    return true;
                end;
            else
                return math.abs(p51.Value) - math.abs(p52.Value);
            end;
        end)
    end;
    v_u_22.get_top_stats = function(_, p55, p56) --[[ Name: get_top_stats ]] --[[ Line: 106 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_9, (ref 3): v_u_1, (ref 4): v_u_4 ]]
        local v57 = p55:get_gear_statmodifierobj()
        local v58 = v_u_2:new()
        for v59, v60 in pairs(v57) do
            v58:add(v59, v60)
        end;
        local v61 = v_u_2:new()
        local l_Upgrades_0 = p56.Upgrades
        for v62 = 1, #l_Upgrades_0 do
            local v63 = v_u_9:singleton():get_equipment_upgrade_for_id(l_Upgrades_0[v62].UpgradeID)
            if v63 ~= nil then
                for v64, v65 in pairs((v63:get_gear_statmodifierobj())) do
                    v61:add(v64, true)
                    if v58:contains(v64) then
                        v58:add(v64, v58:get(v64) + v65)
                    else
                        v58:add(v64, v65)
                    end;
                end;
            end;
        end;
        local v66 = v_u_1:new()
        for v67, v68 in v58:key_itr() do
            v66:push_back({
                ["Stat"] = v67,
                ["Value"] = v68
            })
        end;
        v66:sort(function(p69, p70) --[[ Line: 91 ]]
            --[[ Upvalues: (ref 1): v_u_4 ]]
            local v71 = v_u_4:gearstats_type_to_elemental_color(p69.Stat)
            local v72 = v_u_4:gearstats_type_to_elemental_color(p70.Stat)
            if v71 == nil or v72 == nil then
                if v71 == nil then
                    if v72 == nil then
                        return math.abs(p69.Value) - math.abs(p70.Value);
                    else
                        return false;
                    end;
                else
                    return true;
                end;
            else
                return math.abs(p69.Value) - math.abs(p70.Value);
            end;
        end)
        return v66, v61;
    end;
    local v_u_73 = nil
    local v_u_74 = nil
    local v_u_75 = 0
    local v_u_76 = 0
    v_u_22.visual_update = function(p77, p78) --[[ Name: visual_update ]] --[[ Line: 149 ]]
        --[[ Upvalues: (ref 1): v_u_73, (copy 2): v_u_33, (ref 3): v_u_10, (ref 4): v_u_75, (ref 5): v_u_76 ]]
        if v_u_73 == nil then
            return;
        elseif v_u_73:count() > v_u_33:count() then
            local v79, v80 = v_u_10:incr_wrap(v_u_75, v_u_10:sec_to_tick(2.5) * p78, 1)
            v_u_75 = v79
            if v80 == true then
                v_u_76 = v_u_76 + 1
                if v_u_76 * v_u_33:count() > v_u_73:count() then
                    v_u_76 = 0
                end;
                p77:render_stats_page()
            end;
        end;
    end;
    local v_u_81 = 4
    v_u_22.set_stat_icon_left_margin = function(p82, p83) --[[ Name: set_stat_icon_left_margin ]] --[[ Line: 166 ]]
        --[[ Upvalues: (ref 1): v_u_81 ]]
        v_u_81 = p83
        return p82;
    end;
    v_u_22.render_stats_page = function(_) --[[ Name: render_stats_page ]] --[[ Line: 171 ]]
        --[[ Upvalues: (ref 1): v_u_73, (ref 2): v_u_74, (ref 3): v_u_32, (copy 4): v_u_33, (ref 5): v_u_76, (copy 6): v_u_34, (ref 7): v_u_11, (ref 8): v_u_4, (ref 9): v_u_19, (ref 10): v_u_81 ]]
        if v_u_73 ~= nil and v_u_74 ~= nil then
            if v_u_32 then
                if v_u_73:count() <= v_u_33:count() then
                    v_u_32.Visible = false
                else
                    v_u_32.Visible = true
                    v_u_32.Text = string.format("%d/%d", v_u_76 + 1, (math.ceil(v_u_73:count() / v_u_33:count())))
                end;
            end;
            for v84 = 1, v_u_33:count() do
                local v85 = v_u_33:get(v84)
                local v86 = v84 + v_u_76 * v_u_33:count()
                if v86 <= v_u_73:count() then
                    local v87 = v_u_73:get(v86)
                    if v86 <= v_u_34:count() then
                        local v88 = v_u_11:get_description_for_stat(v87.Stat)
                        if v88 == nil then
                            v_u_34:get(v86).Text = ""
                        else
                            v_u_34:get(v86).Text = v88
                        end;
                    end;
                    local l_Value_0 = v87.Value
                    local l_Stat_0 = v87.Stat
                    v85.TextColor3 = v_u_4:gear_attrvalue_opts_get_color(l_Value_0, l_Stat_0, (v_u_74:contains(l_Stat_0)))
                    v85.Text = string.format("%s%d %s", v87.Value >= 0 and "+" or "-", math.abs(v87.Value), (v_u_4:type_to_name(l_Stat_0)))
                    v_u_19:display_stat_icon_for_sub_text(v85, l_Stat_0, v_u_81)
                else
                    v_u_19:display_stat_icon_for_sub_text(v85, v_u_4.Type.NoStat, 0)
                    v85.Text = ""
                    if v86 <= v_u_34:count() then
                        v_u_34:get(v86).Text = ""
                    end;
                end;
            end;
        end;
    end;
    local function f_set_equipment_data_shared(p89) --[[ Name: set_equipment_data_shared ]] --[[ Line: 233 ]]
        --[[ Upvalues: (ref 1): v_u_75, (ref 2): v_u_76, (ref 3): p_u_21, (ref 4): v_u_23, (ref 5): v_u_24, (ref 6): v_u_4, (copy 7): v_u_22, (ref 8): v_u_30, (ref 9): v_u_8, (ref 10): v_u_31 ]]
        v_u_75 = 0
        v_u_76 = 0
        p_u_21.Visible = true
        if v_u_23 then
            v_u_23.Image = p89:get_icon()
        end;
        if v_u_24 then
            v_u_24.Text = p89:get_name()
            v_u_24.TextColor3 = v_u_4:tier_get_color(p89:get_gear_tier())
        end;
        v_u_22:render_stats_page()
        if v_u_30 then
            v_u_30.Text = v_u_8:slot_to_name(p89:get_avatar_slot())
        end;
        if v_u_31 then
            v_u_31.Image = v_u_8:slot_to_icon(p89:get_avatar_slot())
        end;
    end;
    v_u_22.set_equipment_id = function(p90, p91) --[[ Name: set_equipment_id ]] --[[ Line: 256 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_29, (ref 3): v_u_73, (ref 4): v_u_74, (copy 5): f_set_equipment_data_shared ]]
        local v92 = v_u_5:singleton():get_equipment_for_id(p91)
        if v92 then
            if v_u_29 then
                v_u_29.Text = ""
            end;
            local v93, v94 = p90:get_top_stats(v92, {
                ["Upgrades"] = {}
            })
            v_u_73 = v93
            v_u_74 = v94
            f_set_equipment_data_shared(v92)
        end;
    end;
    v_u_22.set_owned_obj = function(p95, p96, p97) --[[ Name: set_owned_obj ]] --[[ Line: 268 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): p_u_21, (ref 3): v_u_7, (ref 4): v_u_5, (ref 5): v_u_29, (ref 6): v_u_9, (ref 7): v_u_3, (ref 8): v_u_73, (ref 9): v_u_74, (copy 10): f_set_equipment_data_shared ]]
        local v98, v99 = v_u_6:playerblob_ownedid_to_equipmentid(p96, p97)
        if v98 == nil then
            p_u_21.Visible = false
            v_u_7:warnf("GearEquipV2GearStatDisplay:set_owned_obj cannot find owned_id")
        else
            local v100 = v_u_5:singleton():get_equipment_for_id(v98)
            if v100 then
                if v_u_29 then
                    local v101 = v_u_6:get_ownedid_upgrade_count(p96, p97)
                    if v101 == 0 then
                        v_u_29.Text = ""
                    else
                        v_u_29.Text = string.format("+%d", v101)
                        if v_u_9:singleton():upgrade_count_can_upgrade(v101) then
                            v_u_29.TextColor3 = v_u_3:color3(255, 247, 225)
                        else
                            v_u_29.TextColor3 = v_u_3:color3(255, 202, 31)
                        end;
                    end;
                end;
                local v102, v103 = p95:get_top_stats(v100, v99)
                v_u_73 = v102
                v_u_74 = v103
                f_set_equipment_data_shared(v100)
            end;
        end;
    end;
    v_u_22.set_pet_ownedid = function(p104, p105, p106) --[[ Name: set_pet_ownedid ]] --[[ Line: 298 ]]
        --[[ Upvalues: (ref 1): v_u_73, (ref 2): v_u_1, (ref 3): v_u_74, (ref 4): v_u_2, (ref 5): v_u_13, (ref 6): v_u_4, (ref 7): v_u_75, (ref 8): v_u_76, (ref 9): p_u_21 ]]
        v_u_73 = v_u_1:new()
        v_u_74 = v_u_2:new()
        local v107 = v_u_13:playerblob_get_pet_ownedid_ownedpet(p105, p106)
        local v108 = v_u_4:statsdict_base()
        v_u_13:playerblob_apply_pet_ownedid_statsdict(p105, v_u_13:ownedpet_get_ownedid(v107), v108)
        for v109, v110 in pairs(v108) do
            if v110 > 0 or v110 < 0 then
                v_u_73:push_back({
                    ["Stat"] = v109,
                    ["Value"] = v110
                })
            end;
        end;
        v_u_73:sort(function(p111, p112) --[[ Line: 91 ]]
            --[[ Upvalues: (ref 1): v_u_4 ]]
            local v113 = v_u_4:gearstats_type_to_elemental_color(p111.Stat)
            local v114 = v_u_4:gearstats_type_to_elemental_color(p112.Stat)
            if v113 == nil or v114 == nil then
                if v113 == nil then
                    if v114 == nil then
                        return math.abs(p111.Value) - math.abs(p112.Value);
                    else
                        return false;
                    end;
                else
                    return true;
                end;
            else
                return math.abs(p111.Value) - math.abs(p112.Value);
            end;
        end)
        v_u_75 = 0
        v_u_76 = 0
        p_u_21.Visible = true
        p104:render_stats_page()
    end;
    v_u_22.set_hidden = function(_) --[[ Name: set_hidden ]] --[[ Line: 323 ]]
        --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_73, (ref 3): v_u_74 ]]
        p_u_21.Visible = false
        v_u_73 = nil
        v_u_74 = nil
    end;
    v_u_22.set_empty_slot = function(_, p115) --[[ Name: set_empty_slot ]] --[[ Line: 329 ]]
        --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_32, (ref 3): v_u_23, (ref 4): v_u_3, (ref 5): v_u_24, (copy 6): v_u_33, (ref 7): v_u_19, (ref 8): v_u_4, (ref 9): v_u_29, (ref 10): v_u_30, (ref 11): v_u_8, (ref 12): v_u_31, (ref 13): v_u_73, (ref 14): v_u_74 ]]
        p_u_21.Visible = true
        if v_u_32 then
            v_u_32.Visible = false
        end;
        if v_u_23 then
            v_u_23.Image = v_u_3:get_white_assetid()
        end;
        if v_u_24 then
            v_u_24.Text = ""
        end;
        for v116 = 1, 4 do
            local v117 = v_u_33:get(v116)
            v117.Text = ""
            v_u_19:display_stat_icon_for_sub_text(v117, v_u_4.Type.NoStat, 0)
        end;
        if v_u_29 then
            v_u_29.Text = ""
        end;
        if v_u_30 then
            v_u_30.Text = v_u_8:slot_to_name(p115)
        end;
        if v_u_31 then
            v_u_31.Image = v_u_8:slot_to_icon(p115)
        end;
        v_u_73 = nil
        v_u_74 = nil
    end;
    v_u_22:cons()
    return v_u_22;
end;
return v_u_19;
