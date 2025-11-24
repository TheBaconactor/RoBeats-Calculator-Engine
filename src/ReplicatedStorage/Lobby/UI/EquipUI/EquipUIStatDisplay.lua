-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:57 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_2 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_5 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Lobby.UI.EquipUI.GearItemDisplay)
local v_u_8 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_9 = require(game.ReplicatedStorage.Shared.TextSizeCache)
local v_u_10 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_11 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_12 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_13 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_14 = require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_15 = require(game.ReplicatedStorage.Pets.PetUtils)
local v16 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_17 = nil
v16:require_client(function() --[[ Line: 20 ]]
    --[[ Upvalues: (ref 1): v_u_17 ]]
    v_u_17 = require(game.ReplicatedStorage.Lobby.Menus.TrainPetUI)
end)
local v18 = {}
local v_u_19 = v_u_4:new():push_back_table_list({
    v_u_5.Blue,
    v_u_5.Green,
    v_u_5.Orange,
    v_u_5.Purple,
    v_u_5.Red
})
v18.new = function(_, p_u_20, p_u_21, p_u_22, p_u_23, p_u_24) --[[ Name: new ]] --[[ Line: 34 ]]
    --[[ Upvalues: (copy 1): v_u_10, (copy 2): v_u_12, (copy 3): v_u_11, (copy 4): v_u_13, (ref 5): v_u_17, (copy 6): v_u_1, (copy 7): v_u_2, (copy 8): v_u_5, (copy 9): v_u_9, (copy 10): v_u_4, (copy 11): v_u_3, (copy 12): v_u_19, (copy 13): v_u_6, (copy 14): v_u_7, (copy 15): v_u_8, (copy 16): v_u_15, (copy 17): v_u_14 ]]
    local v25 = {}
    local v_u_26 = nil
    local v_u_27 = nil
    local v_u_28 = nil
    local v_u_29 = nil
    local v_u_30 = nil
    local v_u_31 = nil
    v25.get_displayed_ownedid = function(_) --[[ Name: get_displayed_ownedid ]] --[[ Line: 46 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return v_u_29;
    end;
    v25.get_displayed_pet_ownedid = function(_) --[[ Name: get_displayed_pet_ownedid ]] --[[ Line: 47 ]]
        --[[ Upvalues: (ref 1): v_u_30 ]]
        return v_u_30;
    end;
    v25.cons = function(_) --[[ Name: cons ]] --[[ Line: 49 ]]
        --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_26, (ref 3): v_u_27, (ref 4): v_u_10, (ref 5): v_u_28, (ref 6): v_u_31, (copy 7): p_u_24, (copy 8): p_u_20, (ref 9): v_u_12, (ref 10): v_u_11, (copy 11): p_u_21, (ref 12): v_u_13, (ref 13): v_u_30, (ref 14): v_u_17, (copy 15): p_u_22 ]]
        local l_StatDisplaySection_0 = p_u_23.MainSurface.SurfaceGui.Frame.LoadedSection.StatDisplaySection
        v_u_26 = l_StatDisplaySection_0.OverallStatDisplay
        v_u_27 = l_StatDisplaySection_0.SelectedItemStatDisplay
        if v_u_10.DebugMinisActive == true then
            v_u_28 = l_StatDisplaySection_0.SelectedPetStatDisplay
            v_u_31 = p_u_24:add_cycle_element(p_u_20, 1, v_u_12:new(v_u_11:new(p_u_24, p_u_23.PrimaryPart, p_u_23.Buttons.MinisButton), p_u_21, function() --[[ Line: 59 ]]
                --[[ Upvalues: (ref 1): p_u_20, (ref 2): v_u_13, (ref 3): p_u_24, (ref 4): v_u_30, (ref 5): v_u_17, (ref 6): p_u_21, (ref 7): p_u_22 ]]
                p_u_20._sfx_manager:play_sfx(v_u_13.SFX_MENU_OPEN)
                p_u_24:save_equip_changes(function() --[[ Line: 61 ]]
                    --[[ Upvalues: (ref 1): v_u_30, (ref 2): p_u_20, (ref 3): v_u_17, (ref 4): p_u_21, (ref 5): p_u_22 ]]
                    if v_u_30 ~= nil then
                        p_u_20._menus:push_menu(v_u_17:new(p_u_20, p_u_21, p_u_22, v_u_30))
                    end;
                end)
            end))
            v_u_31:set_visible(false)
        end;
        v_u_26.Visible = false
        v_u_27.Visible = false
        if v_u_28 then
            v_u_28.Visible = false
        end;
    end;
    v25.set_display_overall_stats = function(_) --[[ Name: set_display_overall_stats ]] --[[ Line: 79 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_27, (ref 3): v_u_28, (ref 4): v_u_31, (ref 5): v_u_29, (ref 6): v_u_30, (copy 7): p_u_20, (ref 8): v_u_1, (ref 9): v_u_2, (ref 10): v_u_5, (ref 11): v_u_9, (ref 12): v_u_4, (ref 13): v_u_3, (ref 14): v_u_19 ]]
        v_u_26.Visible = true
        v_u_27.Visible = false
        if v_u_28 then
            v_u_28.Visible = false
        end;
        if v_u_31 then
            v_u_31:set_visible(false)
        end;
        v_u_29 = nil
        v_u_30 = nil
        local v32 = p_u_20._player_blob_manager:get_player_blob()
        local l_BaseStatSection_0 = v_u_26.BaseStatSection
        local v33 = v_u_1:get_playerblob_statsdict(v32, p_u_20._player_blob_manager:get_dayid(), p_u_20._player_blob_manager:get_weekid())
        local v34 = v_u_2:statsdict_get_ranked_colors(v33)
        local l_GearPowerDisplay_0 = v_u_26.GearPowerDisplay
        local l_GearPowerBonus_0 = v_u_26.GearPowerDisplay.GearPowerBonus
        if v34:count() >= 1 then
            l_GearPowerBonus_0.PrimaryElementIcon.Image = v_u_5:color_to_iconimage(v34:get(1))
        end;
        if v34:count() >= 2 then
            l_GearPowerBonus_0.PrimaryElementIcon.SecondaryElementIcon.Image = v_u_5:color_to_iconimage(v34:get(2))
        end;
        l_GearPowerDisplay_0.Text = tostring(v_u_1:get_playerblob_base_gearpower_v2(v32, p_u_20._player_blob_manager:get_dayid(), p_u_20._player_blob_manager:get_weekid()))
        l_GearPowerBonus_0.Position = UDim2.new(0, v_u_9:get_text_size(l_GearPowerDisplay_0.Text, l_GearPowerDisplay_0.TextSize, l_GearPowerDisplay_0.Font, Vector2.new(10000, 10000)).X + 4, 0, 0)
        l_GearPowerBonus_0.Text = string.format("+ %d", v_u_1:get_playerblob_color_list_gearpower(v32, v34, p_u_20._player_blob_manager:get_dayid(), p_u_20._player_blob_manager:get_weekid()))
        l_GearPowerBonus_0.PrimaryElementIcon.Position = UDim2.new(0, v_u_9:get_text_size(l_GearPowerBonus_0.Text, l_GearPowerBonus_0.TextSize, l_GearPowerBonus_0.Font, Vector2.new(10000, 10000)).X + 4, 0, -2)
        local v35 = v_u_4:new():push_back_table_list({
            v_u_2.Type.PerfectPoints,
            v_u_2.Type.ComboMultiplier,
            v_u_2.Type.FeverFillRate,
            v_u_2.Type.FeverMultiplier,
            v_u_2.Type.FeverTime,
            v_u_2.Type.PerfectTime
        })
        local v36 = v_u_2:statsdict_base()
        for v37, v38 in v35:key_itr() do
            local v39 = l_BaseStatSection_0:FindFirstChild(string.format("StatDisplay%d", v37))
            v39.NameDisplay.Text = v_u_2:type_to_name(v38)
            v39.Display.Text = tostring(v33[v38])
            v39.BarFillFrame.Fill.Size = UDim2.new(v_u_3:clamp(v33[v38], 0, v_u_2:get_stat_max()) / v_u_2:get_stat_max(), 0, 1, 0)
            if v38 == v_u_2.Type.PerfectPoints then
                v39.SubDisplay.Text = string.format("%dpts", v_u_2:get_perfect_points(v33))
            elseif v38 == v_u_2.Type.ComboMultiplier then
                local _, _, v40 = v_u_2:get_combo_multiplier(v33)
                v39.SubDisplay.Text = string.format("x%.2f", v40)
            elseif v38 == v_u_2.Type.FeverFillRate then
                v39.SubDisplay.Text = string.format("x%.2f", v_u_2:get_fever_fill_base(v33) / v_u_2:get_fever_fill_base(v36))
            elseif v38 == v_u_2.Type.FeverMultiplier then
                v39.SubDisplay.Text = string.format("x%.2f", v_u_2:get_powerbar_multiplier(v33))
            elseif v38 == v_u_2.Type.FeverTime then
                v39.SubDisplay.Text = string.format("x%.2f", v_u_2:get_base_decay_rate(v33) / v_u_2:get_base_decay_rate(v36))
            elseif v38 == v_u_2.Type.PerfectTime then
                local v41, v42 = v_u_2:get_perfect_upper_lower_time(v33)
                v39.SubDisplay.Text = string.format("%dms", (math.floor(math.abs(v41) + math.abs(v42))))
            end;
        end;
        local v43 = 1
        for _, v44 in v_u_19:key_itr() do
            v43 = math.max(v43, v33[v_u_2:elemental_color_to_gearstats_type(v44)])
        end;
        for v45, v46 in v_u_19:key_itr() do
            local v47 = v_u_26.ColorStatSection:FindFirstChild(string.format("ColorDisplay%d", v45))
            v47.ElementIcon.Image = v_u_5:color_to_iconimage(v46)
            v47.ElementNameIcon.Image = v_u_5:color_to_textimage(v46)
            local v48 = v33[v_u_2:elemental_color_to_gearstats_type(v46)]
            v47.Display.Text = tostring(v48)
            v47.BarFillFrame.Fill.ImageColor3 = v_u_5:color_to_color3(v46)
            v47.BarFillFrame.Fill.Size = UDim2.new(v48 / v43, 0, 1, 0)
        end;
    end;
    v25.set_display_ownedid = function(p49, p50) --[[ Name: set_display_ownedid ]] --[[ Line: 168 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_27, (ref 3): v_u_28, (ref 4): v_u_31, (ref 5): v_u_29, (ref 6): v_u_30, (copy 7): p_u_20, (ref 8): v_u_1, (ref 9): v_u_6, (ref 10): v_u_7, (ref 11): v_u_4, (ref 12): v_u_2, (ref 13): v_u_8, (ref 14): v_u_3, (ref 15): v_u_19, (ref 16): v_u_5 ]]
        v_u_26.Visible = false
        v_u_27.Visible = true
        if v_u_28 then
            v_u_28.Visible = false
        end;
        if v_u_31 then
            v_u_31:set_visible(false)
        end;
        v_u_29 = p50
        v_u_30 = nil
        local v51 = p_u_20._player_blob_manager:get_player_blob()
        if p50 == nil or v_u_1:playerblob_ownedid_to_equipmentid(v51, p50) == nil then
            v_u_6:warnf("EquipUIStatDisplay:set_display_gear_item gear_item_display displayed_ownedid nil")
            return p49:set_display_overall_stats();
        end;
        v_u_7:set_display_item_playerblob_ownedid(v_u_27.IconSection, v51, p50)
        v_u_27.UpgradeDisplay.Text = string.format("%d / %d", v_u_1:get_ownedid_upgrade_count(v51, p50), 15)
        v_u_27.BaseGearPowerDisplay.Text = tostring(v_u_1:playerblob_get_ownedid_base_gearpower(v51, p50))
        local v52 = v_u_4:new():push_back_table_list({
            v_u_2.Type.PerfectPoints,
            v_u_2.Type.ComboMultiplier,
            v_u_2.Type.FeverFillRate,
            v_u_2.Type.FeverMultiplier,
            v_u_2.Type.FeverTime,
            v_u_2.Type.PerfectTime
        })
        local v53 = v_u_2:statsdict_base()
        v_u_1:playerblob_apply_ownedid_statsdict(v51, p50, v53)
        local v54 = v_u_1:playerblob_ownedid_to_equipmentid(v51, p50)
        local v55 = v_u_8:singleton():get_equipment_for_id(v54)
        if v55 == nil then
            return v_u_6:warnf("EquipUIStatDisplay:set_display_ownedid(%s) invalid equipmentid(%s)", tostring(p50), (tostring(v54)));
        end;
        local v56 = v55:get_gear_statmodifierobj()
        v_u_27.NameDisplay.Text = v55:get_name()
        v_u_27.NameDisplay.TextColor3 = v_u_2:tier_get_color(v55:get_gear_tier())
        for v57, v58 in v52:key_itr() do
            local v59 = v_u_27.BaseStatSection:FindFirstChild(string.format("StatDisplay%d", v57))
            v59.NameDisplay.Text = v_u_2:type_to_name(v58)
            local v60 = v56[v58] == nil and 0 or v56[v58]
            local v61 = v53[v58]
            if v61 == v60 then
                v59.Display.Text = string.format("%d", v60)
            else
                v59.Display.Text = string.format("%d + <font color=\"rgb(38,239,255)\">%d</font>", v60, v61 - v60)
            end;
            v59.BarFillFrame.FillBack.Size = UDim2.new(v_u_3:clamp(v61, 0, v_u_2:get_stat_max()) / v_u_2:get_stat_max(), 0, 1, 0)
            v59.BarFillFrame.FillFront.Size = UDim2.new(v_u_3:clamp(v60, 0, v_u_2:get_stat_max()) / v_u_2:get_stat_max(), 0, 1, 0)
        end;
        local v62 = 1
        for _, v63 in v_u_19:key_itr() do
            v62 = math.max(v62, v53[v_u_2:elemental_color_to_gearstats_type(v63)])
        end;
        for v64, v65 in v_u_19:key_itr() do
            local v66 = v_u_27.ColorStatSection:FindFirstChild(string.format("ColorDisplay%d", v64))
            v66.ElementIcon.Image = v_u_5:color_to_iconimage(v65)
            v66.ElementNameIcon.Image = v_u_5:color_to_textimage(v65)
            local v67 = v_u_2:elemental_color_to_gearstats_type(v65)
            local v68 = v56[v67] == nil and 0 or v56[v67]
            local v69 = v53[v_u_2:elemental_color_to_gearstats_type(v65)]
            if v69 == v68 then
                v66.Display.Text = string.format("%d", v68)
            else
                v66.Display.Text = string.format("%d + <font color=\"rgb(38,239,255)\">%d</font>", v68, v69 - v68)
            end;
            v66.BarFillFrame.FillFront.ImageColor3 = v_u_5:color_to_color3(v65)
            v66.BarFillFrame.FillFront.Size = UDim2.new(v68 / v62, 0, 1, 0)
            v66.BarFillFrame.FillBack.Size = UDim2.new(v69 / v62, 0, 1, 0)
        end;
    end;
    v25.set_display_pet_ownedid = function(p70, p71) --[[ Name: set_display_pet_ownedid ]] --[[ Line: 269 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_27, (ref 3): v_u_29, (ref 4): v_u_30, (ref 5): v_u_28, (ref 6): v_u_31, (copy 7): p_u_20, (ref 8): v_u_15, (ref 9): v_u_6, (ref 10): v_u_14, (ref 11): v_u_7, (ref 12): v_u_3, (ref 13): v_u_2, (ref 14): v_u_19, (ref 15): v_u_5, (ref 16): v_u_4, (ref 17): v_u_1 ]]
        v_u_26.Visible = false
        v_u_27.Visible = false
        v_u_29 = nil
        v_u_30 = p71
        if v_u_28 ~= nil then
            v_u_28.Visible = true
            if v_u_31 then
                v_u_31:set_visible(true)
            end;
            local v_u_72 = v_u_28
            local v73 = p_u_20._player_blob_manager:get_player_blob()
            local v74 = v_u_15:playerblob_get_pet_ownedid_ownedpet(v73, v_u_30)
            if v74 == nil then
                v_u_6:warnf("EquipUIStatDisplay:set_display_pet_ownedid not found")
                return p70:set_display_overall_stats();
            end;
            local v75 = v_u_15:ownedpet_get_petid(v74)
            local v76 = v_u_14:singleton():get_data_for_petid(v75)
            if v_u_14:singleton():contains_petid(v75) ~= true or v76 == nil then
                return v_u_6:warnf("EquipUIStatDisplay:set_display_pet_ownedid petid not found(%s)", (tostring(v75)));
            end;
            v_u_7:set_display_item_playerblob_pet_ownedid(v_u_72.IconSection, v73, v_u_30)
            local v77 = v_u_15:ownedpet_get_level(v74)
            local v78 = v_u_15:ownedpet_get_max_level(v74)
            v_u_72.NameDisplay.Text = v76:get_name()
            v_u_72.LevelDisplay.Text = string.format("%d / %d", v77, v78)
            v_u_72.RankDisplay.Text = string.format("%d", v_u_15:ownedpet_get_rank(v74))
            v_u_72.RaritySection.Icon.Image = v_u_15:pet_rarity_to_icon(v76:get_rarity())
            local function f_set_bar_num_div(p79, p80) --[[ Name: set_bar_num_div ]] --[[ Line: 303 ]]
                --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_72 ]]
                local v81 = Vector2.new(437, 24)
                local v82 = Vector2.new(353, 22)
                local v83 = v_u_3:clamp(p79 / p80, 0, 1)
                local l_ExpDisplay_0 = v_u_72.ExpBarSection.ExpDisplay
                local l_BarFillYellow_0 = v_u_72.ExpBarSection.BarFillYellow
                l_ExpDisplay_0.Text = string.format("%s / %s", v_u_3:comma_value(p79), v_u_3:comma_value(p80))
                l_BarFillYellow_0.ImageRectSize = v81 * Vector2.new(v83, 1)
                l_BarFillYellow_0.Size = UDim2.new(0, v82.X * v83, 0, v82.Y)
            end;
            if v77 < v78 then
                f_set_bar_num_div(v_u_15:ownedpet_get_exp(v74) - v_u_15:get_exp_to_level(v77, v_u_15:ownedpet_get_rarity(v74)), (v_u_15:get_exp_for_next_level(v77, v_u_15:ownedpet_get_rarity(v74))))
            else
                local v84 = v_u_15:get_exp_for_next_level(v77 - 1, v_u_15:ownedpet_get_rarity(v74))
                f_set_bar_num_div(v84, v84)
            end;
            local v85 = v_u_2:statsdict_base()
            v_u_15:playerblob_apply_pet_ownedid_statsdict(v73, v_u_30, v85)
            local v86 = 1
            for _, v87 in v_u_19:key_itr() do
                v86 = math.max(v86, v85[v_u_2:elemental_color_to_gearstats_type(v87)])
            end;
            for v88, v89 in v_u_19:key_itr() do
                local v90 = v_u_72.ColorStatSection:FindFirstChild(string.format("ColorDisplay%d", v88))
                v90.ElementIcon.Image = v_u_5:color_to_iconimage(v89)
                v90.ElementNameIcon.Image = v_u_5:color_to_textimage(v89)
                local v91 = v_u_2:elemental_color_to_gearstats_type(v89)
                local v92 = v85[v91] == nil and 0 or v85[v91]
                v90.Display.Text = string.format("%d", v92)
                v90.BarFillFrame.FillFront.ImageColor3 = v_u_5:color_to_color3(v89)
                v90.BarFillFrame.FillFront.Size = UDim2.new(v92 / v86, 0, 1, 0)
            end;
            local v93 = v_u_4:new():push_back_table_list({ v_u_72.BaseStatSection.StatDisplay1 })
            for v94, _ in v_u_1:get_base_gearpower_counted_stat_types():key_itr() do
                if v85[v94] ~= nil and v85[v94] > 0 then
                    local v95 = v93:pop_front()
                    v95.NameDisplay.Text = v_u_2:type_to_name(v94)
                    v95.Display.Text = tostring(v85[v94])
                    v95.BarFillFrame.Fill.Size = UDim2.new(v_u_3:clamp(v85[v94], 0, v_u_2:get_stat_max()) / v_u_2:get_stat_max(), 0, 1, 0)
                end;
                if v93:count() == 0 then
                    break;
                end;
            end;
        end;
    end;
    v25:cons()
    return v25;
end;
return v18;
