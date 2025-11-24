-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:54 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Menu.SPUIButton)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_5 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_6 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_8 = require(game.ReplicatedStorage.Avatar.ElementalColor)
return {
    ["new"] = function(_, p_u_9, p_u_10, _, p_u_11) --[[ Name: new ]] --[[ Line: 21 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_7, (copy 4): v_u_4, (copy 5): v_u_8, (copy 6): v_u_1, (copy 7): v_u_5, (copy 8): v_u_6 ]]
        local v12 = v_u_3:SPUIObjectBase()
        local v_u_13 = 1
        local v_u_14 = 1
        local v_u_15 = nil
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = nil
        local v_u_19 = nil
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = nil
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
        local v_u_33 = nil
        local v_u_34 = nil
        local v_u_35 = v_u_2:new()
        v12.cons = function(p36) --[[ Name: cons ]] --[[ Line: 36 ]]
            --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_16, (ref 3): v_u_17, (ref 4): v_u_18, (ref 5): v_u_19, (ref 6): v_u_20, (ref 7): v_u_21, (ref 8): v_u_22, (ref 9): v_u_23, (ref 10): v_u_24, (ref 11): v_u_25, (ref 12): v_u_26, (ref 13): v_u_27, (ref 14): v_u_28, (ref 15): v_u_29, (ref 16): v_u_30, (ref 17): v_u_31, (ref 18): v_u_32, (ref 19): v_u_33, (ref 20): v_u_15, (ref 21): v_u_7, (ref 22): v_u_34, (ref 23): v_u_4, (copy 24): v_u_35, (ref 25): v_u_8 ]]
            p36._native_size = p_u_11.PrimaryPart.Size
            p36._size = p36._native_size
            local l_Frame_0 = p_u_11.MainSurface.SurfaceGui.Frame
            local l_NoteStats_0 = l_Frame_0.NoteStats
            v_u_16 = l_NoteStats_0.PerfectStatsDisplay.PointsDisplay
            v_u_17 = l_NoteStats_0.PerfectStatsDisplay.TimeDisplay
            v_u_18 = l_NoteStats_0.GreatStatsDisplay.PointsDisplay
            v_u_19 = l_NoteStats_0.GreatStatsDisplay.TimeDisplay
            v_u_20 = l_NoteStats_0.OkayStatsDisplay.PointsDisplay
            v_u_21 = l_NoteStats_0.OkayStatsDisplay.TimeDisplay
            v_u_22 = l_NoteStats_0.MissStatsDisplay.ComboBreakDisplay
            local l_ComboStats_0 = l_Frame_0.ComboStats
            v_u_23 = l_ComboStats_0.Lvl3.ComboDisplay
            v_u_24 = l_ComboStats_0.Lvl3.MultiplierDisplay
            v_u_25 = l_ComboStats_0.Lvl2.ComboDisplay
            v_u_26 = l_ComboStats_0.Lvl2.MultiplierDisplay
            v_u_27 = l_ComboStats_0.Lvl1.ComboDisplay
            v_u_28 = l_ComboStats_0.Lvl1.MultiplierDisplay
            local l_FeverStats_0 = l_Frame_0.FeverStats
            v_u_29 = l_FeverStats_0.FillRateDisplay
            v_u_30 = l_FeverStats_0.DrainRateDisplay
            v_u_31 = l_FeverStats_0.MultiplierDisplay
            v_u_32 = l_FeverStats_0.NoteSpeedDisplay
            v_u_33 = l_FeverStats_0.BaseTimeDisplay
            v_u_15 = l_Frame_0.GearPowerStats.GearPowerDisplay
            if v_u_7.ColorGearStatsEnabled == true then
                l_FeverStats_0.NoteSpeedText.Visible = false
                v_u_34 = v_u_4:new(p36, p_u_11.PrimaryPart, p_u_11.ColorStats)
                v_u_35:add_table({
                    [v_u_8.Blue] = p_u_11.ColorStats.SurfaceGui.Frame.ColorStatBlue.Text,
                    [v_u_8.Green] = p_u_11.ColorStats.SurfaceGui.Frame.ColorStatGreen.Text,
                    [v_u_8.Purple] = p_u_11.ColorStats.SurfaceGui.Frame.ColorStatPurple.Text,
                    [v_u_8.Red] = p_u_11.ColorStats.SurfaceGui.Frame.ColorStatRed.Text,
                    [v_u_8.Orange] = p_u_11.ColorStats.SurfaceGui.Frame.ColorStatOrange.Text
                })
            end;
            p36:refresh_ui()
        end;
        local function f_cmp_textcolor(p37, p38, p39) --[[ Name: cmp_textcolor ]] --[[ Line: 83 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            if p39 == true then
                local v40 = p37
                p37 = p38
                p38 = v40
            end;
            if p38 < p37 then
                return v_u_1:color3(56, 252, 64);
            elseif p37 < p38 then
                return v_u_1:color3(252, 52, 73);
            else
                return v_u_1:color3(255, 255, 255);
            end;
        end;
        local function f_timewindow_set(p41, p42, p43) --[[ Name: timewindow_set ]] --[[ Line: 97 ]]
            --[[ Upvalues: (copy 1): f_cmp_textcolor ]]
            local v44, v45 = p41()
            local v46, v47 = p42()
            local v48 = math.abs(v44) + math.abs(v45)
            local v49 = math.abs(v46) + math.abs(v47)
            p43.Text = string.format("%d ms", (math.floor(v48)))
            p43.TextColor3 = f_cmp_textcolor(v48, v49)
        end;
        local function _(p50, p51, p52, p53, p54) --[[ Name: value_set ]] --[[ Line: 105 ]]
            --[[ Upvalues: (copy 1): f_cmp_textcolor ]]
            p52.Text = string.format(p53, p50)
            p52.TextColor3 = f_cmp_textcolor(p50, p51, p54)
        end;
        local function _(p55, p56, p57, p58, p59, p60) --[[ Name: relative_value_set ]] --[[ Line: 109 ]]
            --[[ Upvalues: (copy 1): f_cmp_textcolor ]]
            local v61
            if p60 == true then
                v61 = p56 / p55
            else
                v61 = p55 / p56
            end;
            p57.Text = string.format(p58, v61)
            p57.TextColor3 = f_cmp_textcolor(v61, 1, p59)
        end;
        local function _(_, _) end;
        v12.refresh_ui = function(_) --[[ Name: refresh_ui ]] --[[ Line: 122 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_5, (ref 3): v_u_6, (ref 4): v_u_15, (copy 5): f_timewindow_set, (ref 6): v_u_17, (ref 7): v_u_16, (copy 8): f_cmp_textcolor, (ref 9): v_u_19, (ref 10): v_u_18, (ref 11): v_u_21, (ref 12): v_u_20, (ref 13): v_u_22, (ref 14): v_u_27, (ref 15): v_u_25, (ref 16): v_u_23, (ref 17): v_u_28, (ref 18): v_u_26, (ref 19): v_u_24, (ref 20): v_u_29, (ref 21): v_u_30, (ref 22): v_u_31, (ref 23): v_u_7, (ref 24): v_u_32, (ref 25): v_u_33, (copy 26): v_u_35 ]]
            local v62 = p_u_9._player_blob_manager:get_player_blob()
            local v_u_63 = v_u_5:get_playerblob_statsdict(v62, p_u_9._player_blob_manager:get_dayid(), p_u_9._player_blob_manager:get_weekid())
            local v_u_64 = v_u_6:statsdict_base()
            v_u_15.Text = string.format("%d", v_u_5:get_playerblob_base_gearpower_v2(v62, p_u_9._player_blob_manager:get_dayid(), p_u_9._player_blob_manager:get_weekid()))
            f_timewindow_set(function() --[[ Line: 129 ]]
                --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_63 ]]
                return v_u_6:get_perfect_upper_lower_time(v_u_63);
            end, function() --[[ Line: 129 ]]
                --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_64 ]]
                return v_u_6:get_perfect_upper_lower_time(v_u_64);
            end, v_u_17)
            local v65 = v_u_6:get_perfect_points(v_u_63)
            local v66 = v_u_6:get_perfect_points(v_u_64)
            local v67 = v_u_16
            v67.Text = string.format("%d", v65)
            v67.TextColor3 = f_cmp_textcolor(v65, v66, nil)
            f_timewindow_set(function() --[[ Line: 131 ]]
                --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_63 ]]
                return v_u_6:get_great_upper_lower_time(v_u_63);
            end, function() --[[ Line: 131 ]]
                --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_64 ]]
                return v_u_6:get_great_upper_lower_time(v_u_64);
            end, v_u_19)
            local v68 = v_u_6:get_great_points(v_u_63)
            local v69 = v_u_6:get_great_points(v_u_64)
            local v70 = v_u_18
            v70.Text = string.format("%d", v68)
            v70.TextColor3 = f_cmp_textcolor(v68, v69, nil)
            f_timewindow_set(function() --[[ Line: 133 ]]
                --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_63 ]]
                return v_u_6:get_okay_upper_lower_time(v_u_63);
            end, function() --[[ Line: 133 ]]
                --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_64 ]]
                return v_u_6:get_okay_upper_lower_time(v_u_64);
            end, v_u_21)
            local v71 = v_u_6:get_okay_points(v_u_63)
            local v72 = v_u_6:get_okay_points(v_u_64)
            local v73 = v_u_20
            v73.Text = string.format("%d", v71)
            v73.TextColor3 = f_cmp_textcolor(v71, v72, nil)
            local v74 = v_u_6:get_chain_break_multiplier(v_u_63)
            local v75 = v_u_6:get_chain_break_multiplier(v_u_64)
            local v76 = v_u_22
            v76.Text = string.format("x%.2f", v74)
            v76.TextColor3 = f_cmp_textcolor(v74, v75, nil)
            local v77, v78, v79 = v_u_6:get_combo_thresholds(v_u_63)
            local v80, v81, v82 = v_u_6:get_combo_thresholds(v_u_64)
            local v83 = v_u_27
            v83.Text = string.format("%d", v77)
            v83.TextColor3 = f_cmp_textcolor(v77, v80, true)
            local v84 = v_u_25
            v84.Text = string.format("%d", v78)
            v84.TextColor3 = f_cmp_textcolor(v78, v81, true)
            local v85 = v_u_23
            v85.Text = string.format("%d", v79)
            v85.TextColor3 = f_cmp_textcolor(v79, v82, true)
            local v86, v87, v88 = v_u_6:get_combo_multiplier(v_u_63)
            local v89, v90, v91 = v_u_6:get_combo_multiplier(v_u_64)
            local v92 = v_u_28
            v92.Text = string.format("x%.2f", v86)
            v92.TextColor3 = f_cmp_textcolor(v86, v89, nil)
            local v93 = v_u_26
            v93.Text = string.format("x%.2f", v87)
            v93.TextColor3 = f_cmp_textcolor(v87, v90, nil)
            local v94 = v_u_24
            v94.Text = string.format("x%.2f", v88)
            v94.TextColor3 = f_cmp_textcolor(v88, v91, nil)
            local v95 = v_u_29
            local v96 = v_u_6:get_fever_fill_base(v_u_64) / v_u_6:get_fever_fill_base(v_u_63)
            v95.Text = string.format("x%.2f", v96)
            v95.TextColor3 = f_cmp_textcolor(v96, 1, false)
            local v97 = v_u_30
            local v98 = v_u_6:get_fever_miss_drain_pct(v_u_63) / v_u_6:get_fever_miss_drain_pct(v_u_64)
            v97.Text = string.format("x%.2f", v98)
            v97.TextColor3 = f_cmp_textcolor(v98, 1, true)
            local v99 = v_u_6:get_powerbar_multiplier(v_u_63)
            local v100 = v_u_6:get_powerbar_multiplier(v_u_64)
            local v101 = v_u_31
            v101.Text = string.format("x%.2f", v99)
            v101.TextColor3 = f_cmp_textcolor(v99, v100, nil)
            if v_u_7.ColorGearStatsEnabled == true then
                v_u_32.Text = ""
            else
                local v102 = v_u_32
                local v103 = v_u_6:get_notespeed_multiplier(v_u_64) / v_u_6:get_notespeed_multiplier(v_u_63)
                v102.Text = string.format("x%.2f", v103)
                v102.TextColor3 = f_cmp_textcolor(v103, 1, false)
            end;
            local v104 = v_u_6:get_base_decay_rate(v_u_63)
            local v105 = v_u_6:get_base_decay_rate(v_u_64)
            local v106 = v_u_33
            v106.Text = string.format("%.2f%%", v104)
            v106.TextColor3 = f_cmp_textcolor(v104, v105, nil)
            if v_u_7.ColorGearStatsEnabled == true then
                for v107, v108 in v_u_35:key_itr() do
                    local v109 = v_u_63[v_u_6:elemental_color_to_gearstats_type(v107)]
                    v108.Text = tostring(v109)
                    if v109 > 0 then
                        v108.TextColor3 = Color3.fromRGB(255, 255, 255)
                    else
                        v108.TextColor3 = Color3.fromRGB(170, 170, 170)
                    end;
                end;
            end;
        end;
        v12.layout = function(p110) --[[ Name: layout ]] --[[ Line: 175 ]]
            --[[ Upvalues: (copy 1): p_u_10, (ref 2): v_u_14, (copy 3): p_u_11, (ref 4): v_u_34 ]]
            p110:opt_rescale_to_max_nxy(p_u_10, 0.4, 0.45, v_u_14)
            local v111, v112 = p110:opt_update_cframe_params(p_u_10, {
                ["PositionNXY"] = Vector2.new(0.485, 1),
                ["OffsetXYZ"] = p110:anchored_offset(0.5, 1) + Vector3.new(0, p_u_10:get_size_from_nxy(0, 0.015).Y),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            })
            if v111 == true then
                p_u_11:SetPrimaryPartCFrame(v112)
            end;
            if v_u_34 then
                v_u_34:layout()
            end;
        end;
        v12.set_alpha = function(_, p113) --[[ Name: set_alpha ]] --[[ Line: 191 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_1, (copy 3): p_u_11 ]]
            if v_u_13 ~= p113 then
                v_u_13 = p113
                v_u_1:r_set_alpha(p_u_11, v_u_13)
            end;
        end;
        v12.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 197 ]]
            --[[ Upvalues: (ref 1): v_u_13 ]]
            return v_u_13;
        end;
        v12.set_scale = function(_, p114) --[[ Name: set_scale ]] --[[ Line: 198 ]]
            --[[ Upvalues: (ref 1): v_u_14 ]]
            v_u_14 = p114
        end;
        v12.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 199 ]]
            --[[ Upvalues: (ref 1): v_u_14 ]]
            return v_u_14;
        end;
        v12.get_native_size = function(p115) --[[ Name: get_native_size ]] --[[ Line: 201 ]]
            return p115._native_size;
        end;
        v12.get_size = function(p116) --[[ Name: get_size ]] --[[ Line: 204 ]]
            return p116._size;
        end;
        v12.set_size = function(p117, p118) --[[ Name: set_size ]] --[[ Line: 207 ]]
            --[[ Upvalues: (copy 1): p_u_11 ]]
            p117._size = p118
            p_u_11.PrimaryPart.Size = Vector3.new(p118.X, p118.Y, 0)
        end;
        v12.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 211 ]]
            --[[ Upvalues: (copy 1): p_u_11 ]]
            return p_u_11.PrimaryPart.Position;
        end;
        v12.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 214 ]]
            --[[ Upvalues: (copy 1): p_u_11 ]]
            return p_u_11.PrimaryPart.SurfaceGui;
        end;
        v12:cons()
        return v12;
    end
};
