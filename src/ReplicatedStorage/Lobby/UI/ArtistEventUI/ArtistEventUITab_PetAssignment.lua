-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:58 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_9 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_10 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_12 = require(game.ReplicatedStorage.Lobby.UI.TabControllerBase)
local v_u_13 = require(game.ReplicatedStorage.Shared.ListAdapter)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_14 = require(game.ReplicatedStorage.AudioData.AudioMod)
require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_15 = require(game.ReplicatedStorage.Pets.PetAssignmentInfo)
local v_u_16 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_17 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_18 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_19 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_20 = require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_21 = require(game.ReplicatedStorage.Pets.PetUtils)
local v22 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_23 = nil
local v_u_24 = nil
v22:require_client(function() --[[ Line: 35 ]]
    --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_24 ]]
    v_u_23 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_24 = require(game.ReplicatedStorage.Lobby.Menus.ArtistEventUI)
end)
local v_u_80 = {
    ["Mode"] = {
        ["Loading"] = 1,
        ["Loaded"] = 2
    },
    ["select_song_from_set"] = function(_, p25, p_u_26, p_u_27) --[[ Name: select_song_from_set ]] --[[ Line: 902 ]]
        --[[ Upvalues: (ref 1): v_u_23, (copy 2): v_u_2, (copy 3): v_u_10, (copy 4): v_u_18 ]]
        p25._menus:push_menu(v_u_23:new(p25, p25._spui, p25._menus, function(p_u_28) --[[ Line: 905 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): p_u_26 ]]
            p_u_28:set_header_text("Select Song")
            p_u_28:set_sub_text("Assigned minis must match an element of the song.")
            v_u_2:for_each_key_value_sorted(p_u_26, function(p29) --[[ Line: 910 ]]
                --[[ Upvalues: (copy 1): p_u_28 ]]
                p_u_28:get_element_list():push_back(p29)
            end, function(p30, p31) --[[ Line: 913 ]]
                return p30 < p31;
            end)
        end, function(p32, p33, p34, _, p35) --[[ Line: 918 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_18 ]]
            p33.Text = v_u_10:singleton():get_title_for_key(p32)
            p34.Image = v_u_10:singleton():get_coverimage_assetid_for_key(p32)
            p35:get_description_display().Text = string.format("Elements: %s", v_u_18:songkey_get_elements_string(p32))
            p35:set_select_button_enabled(true)
        end, function(p36) --[[ Line: 924 ]]
            --[[ Upvalues: (copy 1): p_u_27 ]]
            if p36 ~= nil then
                p_u_27(p36)
            end;
        end)):get_list_adapter():set_do_wrap(true)
    end,
    ["select_assignment_type"] = function(_, p37, p_u_38) --[[ Name: select_assignment_type ]] --[[ Line: 933 ]]
        --[[ Upvalues: (ref 1): v_u_23, (copy 2): v_u_15, (copy 3): v_u_1 ]]
        p37._menus:push_menu(v_u_23:new(p37, p37._spui, p37._menus, function(p39) --[[ Line: 936 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            p39:set_header_text("Set Assignment Duration")
            p39:get_element_list():push_back(v_u_15.AssignmentType.Type1)
            p39:get_element_list():push_back(v_u_15.AssignmentType.Type2)
            p39:get_element_list():push_back(v_u_15.AssignmentType.Type3)
        end, function(p40, p41, p42, _, p43) --[[ Line: 942 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_1 ]]
            p41.Text = v_u_15:assignment_type_to_string(p40)
            p42.Image = v_u_1:important_assetid()
            if p40 == v_u_15.AssignmentType.Type1 then
                p43:get_description_display().Text = string.format("Completes in %d hours. More event points are earned.", v_u_15:assignment_type_to_time_sec(p40) / 60 / 60)
            elseif p40 == v_u_15.AssignmentType.Type2 then
                p43:get_description_display().Text = string.format("Completes in %d hours.", v_u_15:assignment_type_to_time_sec(p40) / 60 / 60)
            elseif p40 == v_u_15.AssignmentType.Type3 then
                p43:get_description_display().Text = string.format("Completes in %d hours. More mini EXP is earned.", v_u_15:assignment_type_to_time_sec(p40) / 60 / 60)
            end;
            p43:set_select_button_enabled(true)
        end, function(p44) --[[ Line: 966 ]]
            --[[ Upvalues: (copy 1): p_u_38 ]]
            if p44 ~= nil then
                p_u_38(p44)
            end;
        end))
    end,
    ["select_pet_from_list"] = function(_, p45, p_u_46, p_u_47, p48, p49, p_u_50) --[[ Name: select_pet_from_list ]] --[[ Line: 974 ]]
        --[[ Upvalues: (copy 1): v_u_21, (copy 2): v_u_11, (copy 3): v_u_18, (copy 4): v_u_2, (copy 5): v_u_20, (ref 6): v_u_23, (copy 7): v_u_19 ]]
        local v_u_51 = v_u_21:playerblob_get_ownedid_to_ownedpet_dict((p45._player_blob_manager:get_player_blob()))
        local v52 = v_u_11:get_event_pet_ids_set(p48)
        local v53 = v_u_18:songkey_get_color_list(p49)
        local v_u_54 = v_u_2:new()
        local v_u_55 = v_u_2:new()
        local v_u_56 = v_u_2:new()
        for v57 = 1, p_u_46:count() do
            local v58 = p_u_46:get(v57)
            local v59 = v_u_21:ownedpet_get_petid(v_u_51:get(v58))
            if v52:contains(v59) then
                v_u_54:add_set(v58)
            else
                local v60 = v_u_20:singleton():get_data_for_petid(v59)
                if v60 then
                    if v_u_18:does_color_lists_match(v60:get_active_ranked_colors_list(), v53) then
                        v_u_55:add_set(v58)
                    else
                        v_u_56:add_set(v58)
                    end;
                end;
            end;
        end;
        p45._menus:push_menu(v_u_23:new(p45, p45._spui, p45._menus, function(p61) --[[ Line: 1012 ]]
            --[[ Upvalues: (copy 1): p_u_46, (copy 2): v_u_54, (copy 3): v_u_55, (copy 4): v_u_56 ]]
            p61:set_header_text("Add Mini")
            p61:set_sub_text("Select Minis with higher power to earn more rewards.")
            for v62 = 1, p_u_46:count() do
                local v63 = p_u_46:get(v62)
                if v_u_54:contains(v63) then
                    p61:get_element_list():push_back(v63)
                end;
            end;
            for v64 = 1, p_u_46:count() do
                local v65 = p_u_46:get(v64)
                if v_u_55:contains(v65) then
                    p61:get_element_list():push_back(v65)
                end;
            end;
            for v66 = 1, p_u_46:count() do
                local v67 = p_u_46:get(v66)
                if v_u_56:contains(v67) then
                    p61:get_element_list():push_back(v67)
                end;
            end;
        end, function(p68, p69, p70, _, p71) --[[ Line: 1035 ]]
            --[[ Upvalues: (ref 1): v_u_21, (copy 2): v_u_51, (copy 3): p_u_47, (ref 4): v_u_20, (copy 5): v_u_55, (copy 6): v_u_54, (ref 7): v_u_19 ]]
            local v72 = v_u_21:ownedpet_get_petid(v_u_51:get(p68))
            p69.Text = string.format("[Power: %d] %s", p_u_47:get(p68), v_u_20:singleton():get_name_for_petid(v72))
            if v_u_55:contains(p68) then
                p69.Text = "(Matching Elements x2 EXP) " .. p69.Text
            end;
            if v_u_54:contains(p68) then
                p69.Text = "(Event Mini x4 EXP) " .. p69.Text
            end;
            p70.Image = v_u_20:singleton():get_data_for_petid(v72):get_icon()
            local v73 = v_u_51:get(p68)
            local v74 = v_u_21:ownedpet_get_level(v73)
            local v75 = v_u_21:ownedpet_get_max_level(v73)
            local v76 = v_u_21:ownedpet_get_exp(v73) - v_u_21:get_exp_to_level(v74, v_u_21:ownedpet_get_rarity(v73))
            local v77 = v_u_21:get_exp_for_next_level(v74, v_u_21:ownedpet_get_rarity(v73))
            if v74 < v75 then
                p71:get_description_display().Text = string.format("Level: %d / %d - Exp: %d / %d - [Elements: %s]", v74, v75, v76, v77, v_u_19:elements_list_get_string(v_u_20:singleton():get_data_for_petid(v72):get_active_ranked_colors_list()))
            else
                local v78 = v_u_21:get_exp_for_next_level(v74 - 1, v_u_21:ownedpet_get_rarity(v73))
                p71:get_description_display().Text = string.format("Level: %d / %d - Exp: %d / %d - [Elements: %s]", v74, v75, v78, v78, v_u_19:elements_list_get_string(v_u_20:singleton():get_data_for_petid(v72):get_active_ranked_colors_list()))
            end;
            p71:set_select_button_enabled(true)
        end, function(p79) --[[ Line: 1080 ]]
            --[[ Upvalues: (copy 1): p_u_50 ]]
            if p79 ~= nil then
                p_u_50(p79)
            end;
        end)):get_list_adapter():set_do_wrap(true)
    end
}
local v_u_81 = false
local v_u_82 = 0
v_u_80.set_notification_display = function(_, p83, p84) --[[ Name: set_notification_display ]] --[[ Line: 45 ]]
    --[[ Upvalues: (ref 1): v_u_81, (ref 2): v_u_82 ]]
    v_u_81 = p83
    v_u_82 = p84
end;
v_u_80.has_notification = function(_) --[[ Name: has_notification ]] --[[ Line: 50 ]]
    --[[ Upvalues: (ref 1): v_u_81, (ref 2): v_u_82 ]]
    return v_u_81, v_u_82;
end;
local v_u_85 = v_u_15.PlayerAssignmentData:new()
local v_u_86 = false
v_u_80.handle_server_push_data = function(_, p87, p88) --[[ Name: handle_server_push_data ]] --[[ Line: 55 ]]
    --[[ Upvalues: (ref 1): v_u_85, (copy 2): v_u_15, (ref 3): v_u_86, (copy 4): v_u_80, (ref 5): v_u_24 ]]
    v_u_85 = v_u_15.PlayerAssignmentData:from_table(p88)
    v_u_86 = true
    for _, v89 in v_u_85:get_assignment_datas():key_itr() do
        if v89:get_end_time() - p87._player_blob_manager:get_global_time() <= 0 then
            v_u_80:set_notification_display(true, 1)
            v_u_24:set_notification_display(true, 1)
        end;
    end;
end;
local v_u_160 = {
    ["new"] = function(_, p_u_90, p_u_91, p_u_92, p_u_93) --[[ Name: new ]] --[[ Line: 73 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_21, (copy 3): v_u_6, (copy 4): v_u_20, (copy 5): v_u_16, (copy 6): v_u_19, (copy 7): v_u_18, (copy 8): v_u_17, (copy 9): v_u_4, (copy 10): v_u_5, (copy 11): v_u_7, (copy 12): v_u_15, (ref 13): v_u_86, (ref 14): v_u_85, (copy 15): v_u_1, (copy 16): v_u_10 ]]
        local v_u_94 = {}
        v_u_94.new = function(_, p_u_95) --[[ Name: new ]] --[[ Line: 76 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_90, (ref 3): v_u_21, (ref 4): v_u_6, (ref 5): v_u_20, (ref 6): v_u_16, (ref 7): v_u_19, (ref 8): v_u_18, (ref 9): v_u_17 ]]
            local v96 = {}
            local v_u_97 = nil
            local v_u_98 = nil
            local v_u_99 = nil
            local v_u_100 = nil
            local v_u_101 = nil
            local v_u_102 = v_u_3:new()
            local function _() --[[ Name: cons ]] --[[ Line: 87 ]]
                --[[ Upvalues: (ref 1): v_u_97, (copy 2): p_u_95, (ref 3): v_u_98, (ref 4): v_u_99, (ref 5): v_u_100, (ref 6): v_u_101, (copy 7): v_u_102 ]]
                v_u_97 = p_u_95.Icon
                v_u_98 = p_u_95.ColorSection
                v_u_99 = p_u_95.GearPowerSection
                v_u_100 = v_u_99.Display
                v_u_101 = p_u_95.UpgradeCountDisplay
                v_u_102:push_back_table_list({
                    p_u_95.ColorSection,
                    p_u_95.GearPowerSection,
                    p_u_95.Icon,
                    p_u_95.UpgradeCountDisplay
                })
            end;
            v96.set_as_songkey_ownedid = function(p103, p104, p105) --[[ Name: set_as_songkey_ownedid ]] --[[ Line: 102 ]]
                --[[ Upvalues: (copy 1): v_u_102, (ref 2): p_u_90, (ref 3): v_u_21, (ref 4): v_u_6, (ref 5): v_u_20, (ref 6): v_u_97, (ref 7): v_u_16, (ref 8): v_u_19, (ref 9): v_u_98, (ref 10): v_u_18, (ref 11): v_u_17, (ref 12): v_u_100, (ref 13): v_u_101 ]]
                for _, v106 in v_u_102:key_itr() do
                    v106.Visible = true
                end;
                local v107 = p_u_90._player_blob_manager:get_player_blob()
                local v108 = v_u_21:playerblob_get_ownedid_to_ownedpet_dict(v107)
                if v108:contains(p105) == true then
                    local v109 = v108:get(p105)
                    local v110 = v_u_20:singleton():get_data_for_petid(v_u_21:ownedpet_get_petid(v109))
                    if v110 ~= nil then
                        v_u_97.Image = v110:get_icon()
                        local v111 = v_u_16:statsdict_base()
                        v_u_21:playerblob_apply_pet_ownedid_statsdict(v107, p105, v111)
                        v_u_19:render_color_section(v_u_98.PrimaryColorIcon, v_u_98.SecondaryColorIcon, (v_u_16:statsdict_get_ranked_colors(v111)))
                        local v112 = v_u_18:songkey_get_color_list(p104)
                        local v113 = v_u_16:statsdict_base()
                        v_u_21:playerblob_apply_pet_ownedid_statsdict(v107, p105, v113)
                        v_u_100.Text = tostring((v_u_17:statsdict_get_gear_power(v113, true, v112)))
                        v_u_101.Text = string.format("Level %d", v_u_21:ownedpet_get_level(v109))
                    end;
                else
                    v_u_6:warnf("PetSectionDisplay:set_as_songkey_ownedid - pet_ownedid not found")
                    return p103:set_as_empty();
                end;
            end;
            v96.set_as_empty = function(_) --[[ Name: set_as_empty ]] --[[ Line: 137 ]]
                --[[ Upvalues: (copy 1): v_u_102 ]]
                for _, v114 in v_u_102:key_itr() do
                    v114.Visible = false
                end;
            end;
            v_u_97 = p_u_95.Icon
            v_u_98 = p_u_95.ColorSection
            v_u_99 = p_u_95.GearPowerSection
            v_u_100 = v_u_99.Display
            v_u_101 = p_u_95.UpgradeCountDisplay
            v_u_102:push_back_table_list({
                p_u_95.ColorSection,
                p_u_95.GearPowerSection,
                p_u_95.Icon,
                p_u_95.UpgradeCountDisplay
            })
            return v96;
        end;
        local v115 = {}
        local v_u_116 = nil
        local v_u_117 = nil
        local v_u_118 = nil
        local v_u_119 = nil
        local v_u_120 = nil
        local v_u_121 = nil
        local v_u_122 = nil
        local v_u_123 = nil
        local v_u_124 = nil
        local v_u_125 = v_u_3:new()
        local v_u_126 = v_u_3:new()
        local v_u_127 = v_u_3:new()
        local v_u_128 = nil
        local v_u_129 = nil
        local v_u_130 = 1
        local v_u_131 = -1
        local function f_cons() --[[ Name: cons ]] --[[ Line: 167 ]]
            --[[ Upvalues: (ref 1): v_u_116, (ref 2): v_u_4, (copy 3): p_u_92, (copy 4): p_u_93, (ref 5): v_u_117, (ref 6): v_u_118, (ref 7): v_u_119, (ref 8): v_u_120, (ref 9): v_u_121, (ref 10): v_u_122, (ref 11): v_u_123, (ref 12): v_u_124, (copy 13): v_u_125, (copy 14): v_u_126, (copy 15): v_u_127, (copy 16): v_u_94, (ref 17): v_u_128, (ref 18): v_u_129, (copy 19): p_u_90, (ref 20): v_u_5, (ref 21): v_u_7, (ref 22): v_u_15, (ref 23): v_u_86, (ref 24): v_u_85, (ref 25): v_u_130, (copy 26): p_u_91 ]]
            v_u_116 = v_u_4:new(p_u_92, p_u_92:get_uichild_parent(), p_u_93.PrimaryPart):set_default_sgui()
            v_u_117 = p_u_93.PrimaryPart.SurfaceGui.Frame
            v_u_118 = v_u_117.AssignmentTimeRemainingDisplay.TimeRemainingDisplay
            v_u_119 = v_u_117.OverallPowerDisplay.TotalPowerDisplay
            v_u_120 = v_u_117.OverallPowerDisplay.BarFillFrame.FillFront
            v_u_121 = v_u_117.SongSection
            v_u_122 = v_u_121.AlbumArt
            v_u_123 = v_u_121.AlbumArtOverlay
            v_u_124 = v_u_121.ColorSection
            v_u_125:push_back_table_list({
                v_u_117.OverallPowerDisplay,
                v_u_117.PetFrame1,
                v_u_117.PetFrame2,
                v_u_117.PetFrame3,
                v_u_117.AssignmentTimeRemainingDisplay,
                v_u_117.SongSection
            })
            v_u_126:push_back_table_list({ v_u_117.NoAssignmentDisplay })
            v_u_127:push_back(v_u_94:new(v_u_117.PetFrame1))
            v_u_127:push_back(v_u_94:new(v_u_117.PetFrame2))
            v_u_127:push_back(v_u_94:new(v_u_117.PetFrame3))
            v_u_128 = p_u_93.ActionButton.SurfaceGui.Frame.TextDisplay
            v_u_129 = p_u_92:add_cycle_element(p_u_90, 1, v_u_5:new(v_u_4:new(v_u_116, p_u_93.PrimaryPart, p_u_93.ActionButton), p_u_90._spui, function() --[[ Line: 198 ]]
                --[[ Upvalues: (ref 1): p_u_90, (ref 2): v_u_7, (ref 3): v_u_15, (ref 4): v_u_86, (ref 5): v_u_85, (ref 6): v_u_130, (ref 7): p_u_91 ]]
                p_u_90._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                local v132 = v_u_15.AssignmentData:get_default()
                if v_u_86 then
                    local v133 = v_u_85:get_assignment_datas()
                    if v_u_130 >= 1 and v_u_130 <= v133:count() then
                        v132 = v133:get(v_u_130)
                    end;
                end;
                if v132 == v_u_15.AssignmentData:get_default() then
                    p_u_91:on_create_new_assignment_pressed()
                    return;
                elseif v132:get_end_time() - p_u_90._player_blob_manager:get_global_time() > 0 then
                    p_u_91:on_cancel_assignment_pressed(v_u_130)
                else
                    p_u_91:on_claim_assignment_pressed(v_u_130)
                end;
            end)):set_auto_zoffset_behaviour(true)
        end;
        local function _() --[[ Name: set_as_no_assignment ]] --[[ Line: 221 ]]
            --[[ Upvalues: (copy 1): v_u_125, (copy 2): v_u_126, (ref 3): v_u_128, (ref 4): v_u_129 ]]
            for _, v134 in v_u_125:key_itr() do
                v134.Visible = false
            end;
            for _, v135 in v_u_126:key_itr() do
                v135.Visible = true
            end;
            v_u_128.Text = "Assign"
            v_u_129:set_visible(true)
        end;
        local function _() --[[ Name: set_as_has_assignment ]] --[[ Line: 232 ]]
            --[[ Upvalues: (copy 1): v_u_125, (copy 2): v_u_126 ]]
            for _, v136 in v_u_125:key_itr() do
                v136.Visible = true
            end;
            for _, v137 in v_u_126:key_itr() do
                v137.Visible = false
            end;
        end;
        local function f_update_time_remaining_display() --[[ Name: update_time_remaining_display ]] --[[ Line: 241 ]]
            --[[ Upvalues: (ref 1): v_u_131, (ref 2): v_u_129, (copy 3): p_u_90, (ref 4): v_u_1, (ref 5): v_u_118, (ref 6): v_u_128 ]]
            if v_u_131 >= 0 then
                if v_u_129:get_visible() then
                    local v138 = v_u_131 - p_u_90._player_blob_manager:get_global_time()
                    local v139, v140
                    if v138 <= 0 then
                        v139 = "Done!"
                        v140 = "Claim"
                    else
                        v139 = v_u_1:format_sec_time(v138)
                        v140 = "Cancel"
                    end;
                    if v139 ~= v_u_118.Text then
                        v_u_118.Text = v139
                    end;
                    if v140 ~= v_u_128.Text then
                        v_u_128.Text = v140
                    end;
                end;
            end;
        end;
        v115.set_player_assignment_index = function(_, p141) --[[ Name: set_player_assignment_index ]] --[[ Line: 265 ]]
            --[[ Upvalues: (ref 1): v_u_130, (copy 2): p_u_90, (ref 3): v_u_15, (ref 4): v_u_86, (ref 5): v_u_85, (copy 6): v_u_125, (copy 7): v_u_126, (ref 8): v_u_128, (ref 9): v_u_129, (ref 10): v_u_131, (ref 11): v_u_18, (ref 12): v_u_16, (ref 13): v_u_21, (ref 14): v_u_17, (ref 15): v_u_119, (ref 16): v_u_1, (ref 17): v_u_120, (ref 18): v_u_10, (ref 19): v_u_122, (ref 20): v_u_123, (ref 21): v_u_124, (copy 22): v_u_127, (copy 23): f_update_time_remaining_display ]]
            v_u_130 = p141
            local v142 = p_u_90._player_blob_manager:get_player_blob()
            local v143 = v_u_15.AssignmentData:get_default()
            if v_u_86 then
                local v144 = v_u_85:get_assignment_datas()
                if p141 >= 1 and p141 <= v144:count() then
                    v143 = v144:get(p141)
                end;
            end;
            if v143 == v_u_15.AssignmentData:get_default() then
                for _, v145 in v_u_125:key_itr() do
                    v145.Visible = false
                end;
                for _, v146 in v_u_126:key_itr() do
                    v146.Visible = true
                end;
                v_u_128.Text = "Assign"
                v_u_129:set_visible(true)
                v_u_131 = -1
            else
                for _, v147 in v_u_125:key_itr() do
                    v147.Visible = true
                end;
                for _, v148 in v_u_126:key_itr() do
                    v148.Visible = false
                end;
                v_u_131 = v143:get_end_time()
                local v149 = v_u_18:songkey_get_color_list(v143:get_song_key())
                local v150 = 0
                for v151, _ in v143:get_pet_owned_id_set():key_itr() do
                    local v152 = v_u_16:statsdict_base()
                    v_u_21:playerblob_apply_pet_ownedid_statsdict(v142, v151, v152)
                    v150 = v150 + v_u_17:statsdict_get_gear_power(v152, true, v149)
                end;
                v_u_119.Text = v_u_1:comma_value(v150)
                v_u_120.Size = UDim2.new(math.min(1, v150 / v_u_15:get_gear_power_calc_range():max()), 0, 1, 0)
                local v153 = v143:get_song_key()
                v_u_10:singleton():render_coverimage_for_key(v_u_122, v_u_123, v153)
                v_u_18:render_songkey_colorsection(v153, v_u_124)
                local v154 = v143:get_pet_owned_id_set():key_list()
                v154:sort(function(p155, p156) --[[ Line: 305 ]]
                    return p155 < p156;
                end)
                for v157 = 1, v_u_127:count() do
                    local v158 = v_u_127:get(v157)
                    if v157 <= v154:count() then
                        v158:set_as_songkey_ownedid(v153, v154:get(v157))
                    else
                        v158:set_as_empty()
                    end;
                end;
                v_u_129:set_visible(true)
                f_update_time_remaining_display()
            end;
        end;
        v115.set_visible = function(_, p159) --[[ Name: set_visible ]] --[[ Line: 321 ]]
            --[[ Upvalues: (ref 1): v_u_116, (ref 2): v_u_129 ]]
            v_u_116:set_visible(p159)
            if p159 ~= true then
                v_u_129:set_visible(false)
            end;
        end;
        v115.update = function(_, _) --[[ Name: update ]] --[[ Line: 328 ]]
            --[[ Upvalues: (copy 1): f_update_time_remaining_display ]]
            f_update_time_remaining_display()
        end;
        v115.layout = function(_) --[[ Name: layout ]] --[[ Line: 332 ]]
            --[[ Upvalues: (ref 1): v_u_116 ]]
            v_u_116:layout()
        end;
        f_cons()
        return v115;
    end
}
v_u_80.new = function(_, p_u_161, p_u_162, p_u_163, p_u_164) --[[ Name: new ]] --[[ Line: 340 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): v_u_80, (copy 3): v_u_5, (copy 4): v_u_4, (copy 5): v_u_7, (copy 6): v_u_9, (copy 7): v_u_3, (copy 8): v_u_15, (copy 9): v_u_13, (ref 10): v_u_86, (ref 11): v_u_85, (copy 12): v_u_160, (ref 13): v_u_81, (copy 14): v_u_8, (copy 15): v_u_6 ]]
    local v_u_165 = v_u_12:new()
    local v_u_166 = nil
    local v_u_167 = nil
    local v_u_168 = nil
    local v_u_169 = nil
    local v_u_170 = nil
    local l_Loading_0 = v_u_80.Mode.Loading
    local function f_cons() --[[ Name: cons ]] --[[ Line: 351 ]]
        --[[ Upvalues: (ref 1): v_u_166, (copy 2): p_u_163, (ref 3): v_u_168, (ref 4): v_u_169, (ref 5): v_u_170, (copy 6): p_u_162, (copy 7): p_u_161, (ref 8): v_u_5, (ref 9): v_u_4, (ref 10): v_u_7, (copy 11): p_u_164, (ref 12): v_u_9, (ref 13): v_u_3, (ref 14): v_u_15, (ref 15): v_u_167, (ref 16): v_u_13, (ref 17): v_u_86, (ref 18): v_u_85, (ref 19): v_u_160, (copy 20): v_u_165 ]]
        v_u_166 = p_u_163.MainSurface.SurfaceGui.Frame.TabPetAssignment
        v_u_166.Visible = false
        v_u_168 = v_u_166.LoadingFrame
        v_u_169 = v_u_166.LoadedFrame
        v_u_170 = p_u_162:add_cycle_element(p_u_161, 1, v_u_5:new(v_u_4:new(p_u_162, p_u_163.PrimaryPart, p_u_163.TabPetAssignmentElements.InfoButton), p_u_161._spui, function() --[[ Line: 361 ]]
            --[[ Upvalues: (ref 1): p_u_161, (ref 2): v_u_7, (ref 3): p_u_164, (ref 4): v_u_9 ]]
            p_u_161._sfx_manager:play_sfx(v_u_7.SFX_MENU_CLOSE)
            p_u_164:push_menu(v_u_9:new(p_u_161, p_u_161._spui, p_u_164):set_text("Mini Training Assignments", "- Assign minis with higher total power to earn more rewards.\n- Change assignment duration to earn more Event Points or EXP\n- Extra Mini EXP will be earned if the mini is featured in the event, or if elements match the song.\n- You cannot assign training on the same song while another assignment is in progress.\n- Every mini can only be assigned to one training at a time.\n- Team contribution points earned count toward the daily \'Song Mission\' point limit.\n- If assignment is claimed during another event, no event points will be earned."))
        end))
        local v_u_171 = v_u_3:new()
        for v172 = 1, v_u_15:get_max_player_assignments() do
            v_u_171:push_back(v172)
        end;
        v_u_167 = v_u_13:new():set_fn_get_data_list(function() --[[ Line: 385 ]]
            --[[ Upvalues: (copy 1): v_u_171 ]]
            return v_u_171;
        end):set_fn_set_element_data(function(p173, p174, _, p175) --[[ Line: 388 ]]
            --[[ Upvalues: (ref 1): v_u_86, (ref 2): v_u_85 ]]
            if p174 ~= nil then
                p173:set_player_assignment_index(p174)
            end;
            if v_u_86 then
                if p175 <= v_u_85:get_assignment_datas():count() + 1 then
                    p173:set_visible(true)
                else
                    p173:set_visible(false)
                end;
            else
                p173:set_visible(false)
                return;
            end;
        end)
        local l_Anchors_0 = p_u_163.TabPetAssignmentElements.Anchors
        v_u_167:create_list_elements_from_anchors_and_proto({ l_Anchors_0.Anchor1, l_Anchors_0.Anchor2, l_Anchors_0.Anchor3 }, p_u_163.TabPetAssignmentElements.Proto, p_u_163, function(p176) --[[ Line: 415 ]]
            --[[ Upvalues: (ref 1): v_u_160, (ref 2): p_u_161, (ref 3): v_u_165, (ref 4): p_u_162 ]]
            p176.Name = "PetAssignmentElement"
            return v_u_160:new(p_u_161, v_u_165, p_u_162, p176);
        end)
        v_u_165:refresh()
    end;
    v_u_165.on_create_new_assignment_pressed = function(_) --[[ Name: on_create_new_assignment_pressed ]] --[[ Line: 424 ]]
        --[[ Upvalues: (ref 1): v_u_80, (copy 2): p_u_161, (ref 3): v_u_167 ]]
        v_u_80:create_new_assignment(p_u_161, function() --[[ Line: 425 ]]
            --[[ Upvalues: (ref 1): v_u_167 ]]
            v_u_167:page_update()
        end)
    end;
    v_u_165.on_cancel_assignment_pressed = function(_, p177) --[[ Name: on_cancel_assignment_pressed ]] --[[ Line: 431 ]]
        --[[ Upvalues: (ref 1): v_u_80, (copy 2): p_u_161, (ref 3): v_u_167 ]]
        v_u_80:cancel_assignment(p_u_161, p177, function() --[[ Line: 432 ]]
            --[[ Upvalues: (ref 1): v_u_167 ]]
            v_u_167:page_update()
        end)
    end;
    v_u_165.on_claim_assignment_pressed = function(_, p178) --[[ Name: on_claim_assignment_pressed ]] --[[ Line: 437 ]]
        --[[ Upvalues: (ref 1): v_u_80, (copy 2): p_u_161, (ref 3): v_u_167 ]]
        v_u_80:claim_assignment(p_u_161, p178, function() --[[ Line: 438 ]]
            --[[ Upvalues: (ref 1): v_u_167 ]]
            v_u_167:page_update()
        end)
    end;
    v_u_165.behaviour_update = function(_, p179) --[[ Name: behaviour_update ]] --[[ Line: 443 ]]
        --[[ Upvalues: (ref 1): v_u_167 ]]
        for _, v180 in v_u_167:get_display_elements():key_itr() do
            v180:update(p179)
        end;
    end;
    local v_u_181 = nil
    v_u_165.set_visible = function(_, p182) --[[ Name: set_visible ]] --[[ Line: 450 ]]
        --[[ Upvalues: (ref 1): v_u_181, (ref 2): v_u_166, (ref 3): v_u_167, (ref 4): v_u_170 ]]
        v_u_181 = p182
        v_u_166.Visible = p182
        if v_u_181 ~= true then
            v_u_167:set_visible(false)
            v_u_170:set_visible(false)
        end;
    end;
    v_u_165.load_data = function(p_u_183, p_u_184) --[[ Name: load_data ]] --[[ Line: 459 ]]
        --[[ Upvalues: (ref 1): v_u_81, (ref 2): l_Loading_0, (ref 3): v_u_80, (copy 4): p_u_162, (copy 5): p_u_161, (ref 6): v_u_8, (ref 7): v_u_85, (ref 8): v_u_15, (ref 9): v_u_86, (ref 10): v_u_6 ]]
        v_u_81 = false
        l_Loading_0 = v_u_80.Mode.Loading
        p_u_183:refresh()
        local v_u_185 = p_u_162:get_last_load_start_time()
        p_u_161._evt:clear_pending_on(v_u_8.EVT_PetAssignment_RequestData_Server)
        p_u_161._evt:wait_on_event_once(v_u_8.EVT_PetAssignment_RequestData_Server, function(p186) --[[ Line: 466 ]]
            --[[ Upvalues: (ref 1): v_u_85, (ref 2): v_u_15, (ref 3): v_u_86, (ref 4): l_Loading_0, (ref 5): v_u_80, (copy 6): v_u_185, (ref 7): p_u_162, (ref 8): v_u_6, (copy 9): p_u_183, (copy 10): p_u_184 ]]
            v_u_85 = v_u_15.PlayerAssignmentData:from_table(p186)
            v_u_86 = true
            l_Loading_0 = v_u_80.Mode.Loaded
            if v_u_185 ~= p_u_162:get_last_load_start_time() then
                return v_u_6:warnf("data load cancelled");
            end;
            p_u_183:refresh()
            if p_u_184 then
                p_u_184()
            end;
        end)
        p_u_161._evt:fire_event_to_server(v_u_8.EVT_PetAssignment_RequestData_Client)
    end;
    v_u_165.refresh = function(_) --[[ Name: refresh ]] --[[ Line: 481 ]]
        --[[ Upvalues: (ref 1): l_Loading_0, (ref 2): v_u_80, (ref 3): v_u_168, (ref 4): v_u_169, (ref 5): v_u_167, (ref 6): v_u_170 ]]
        if l_Loading_0 == v_u_80.Mode.Loading then
            v_u_168.Visible = true
            v_u_169.Visible = false
            v_u_167:set_visible(false)
            v_u_170:set_visible(false)
        elseif l_Loading_0 == v_u_80.Mode.Loaded then
            v_u_168.Visible = false
            v_u_169.Visible = true
            v_u_167:set_visible(true)
            v_u_167:page_update()
            v_u_170:set_visible(true)
        end;
    end;
    v_u_165.layout = function(_) --[[ Name: layout ]] --[[ Line: 496 ]]
        --[[ Upvalues: (ref 1): v_u_167 ]]
        v_u_167:layout()
    end;
    f_cons()
    return v_u_165;
end;
v_u_80.cancel_assignment = function(_, p_u_187, p_u_188, p_u_189) --[[ Name: cancel_assignment ]] --[[ Line: 504 ]]
    --[[ Upvalues: (copy 1): v_u_9, (ref 2): v_u_86, (ref 3): v_u_85, (copy 4): v_u_8, (copy 5): v_u_15 ]]
    local function f_error_popup(p190) --[[ Name: error_popup ]] --[[ Line: 505 ]]
        --[[ Upvalues: (copy 1): p_u_187, (ref 2): v_u_9 ]]
        p_u_187._menus:push_menu(v_u_9:new(p_u_187, p_u_187._spui, p_u_187._menus):set_text("Error", p190))
    end;
    if v_u_86 ~= true then
        return f_error_popup("cached data not loaded");
    end;
    if p_u_188 < 1 or v_u_85:get_assignment_datas():count() < p_u_188 then
        return f_error_popup("Invalid assignment index");
    end;
    p_u_187._menus:push_menu(v_u_9:new(p_u_187, p_u_187._spui, p_u_187._menus):set_text("Confirm", "Are you sure you want to cancel this assignment?"):set_okay_button_fn(function() --[[ Line: 517 ]]
        --[[ Upvalues: (copy 1): p_u_187, (ref 2): v_u_9, (ref 3): v_u_8, (ref 4): v_u_85, (ref 5): v_u_15, (ref 6): v_u_86, (copy 7): p_u_189, (copy 8): p_u_188 ]]
        local v_u_191 = p_u_187._menus:push_menu(v_u_9:new(p_u_187, p_u_187._spui, p_u_187._menus):set_text("Loading", "Cancelling assignment..."):set_close_button_visible(false))
        p_u_187._evt:clear_pending_on(v_u_8.EVT_PetAssignment_CancelAssignment_Server)
        p_u_187._evt:wait_on_event_once(v_u_8.EVT_PetAssignment_CancelAssignment_Server, function(p192, p193, p194) --[[ Line: 521 ]]
            --[[ Upvalues: (ref 1): v_u_85, (ref 2): v_u_15, (ref 3): v_u_86, (ref 4): p_u_187, (ref 5): v_u_9, (ref 6): p_u_189, (copy 7): v_u_191 ]]
            v_u_85 = v_u_15.PlayerAssignmentData:from_table(p194)
            v_u_86 = true
            if p192 ~= true then
                p_u_187._menus:push_menu(v_u_9:new(p_u_187, p_u_187._spui, p_u_187._menus):set_text("Error", p193))
            end;
            if p_u_189 then
                p_u_189()
            end;
            p_u_187._menus:remove_menu(v_u_191)
        end)
        p_u_187._evt:fire_event_to_server(v_u_8.EVT_PetAssignment_CancelAssignment_Client, p_u_188)
    end))
end;
v_u_80.claim_assignment = function(_, p_u_195, p196, p_u_197) --[[ Name: claim_assignment ]] --[[ Line: 538 ]]
    --[[ Upvalues: (copy 1): v_u_9, (ref 2): v_u_86, (ref 3): v_u_85, (copy 4): v_u_8, (copy 5): v_u_15, (copy 6): v_u_7 ]]
    local function f_error_popup(p198) --[[ Name: error_popup ]] --[[ Line: 539 ]]
        --[[ Upvalues: (copy 1): p_u_195, (ref 2): v_u_9 ]]
        p_u_195._menus:push_menu(v_u_9:new(p_u_195, p_u_195._spui, p_u_195._menus):set_text("Error", p198))
    end;
    if v_u_86 ~= true then
        return f_error_popup("cached data not loaded");
    end;
    if p196 < 1 or v_u_85:get_assignment_datas():count() < p196 then
        return f_error_popup("Invalid assignment index");
    end;
    if v_u_85:get_assignment_datas():get(p196):get_end_time() - p_u_195._player_blob_manager:get_global_time() > 0 then
        return f_error_popup("Assignment not completed");
    end;
    local v_u_199 = p_u_195._menus:push_menu(v_u_9:new(p_u_195, p_u_195._spui, p_u_195._menus):set_text("Loading", "Claiming assignment..."):set_close_button_visible(false))
    p_u_195._evt:clear_pending_on(v_u_8.EVT_PetAssignment_ClaimRewards_Server)
    p_u_195._evt:wait_on_event_once(v_u_8.EVT_PetAssignment_ClaimRewards_Server, function(p200, p_u_201, p202) --[[ Line: 551 ]]
        --[[ Upvalues: (ref 1): v_u_85, (ref 2): v_u_15, (ref 3): v_u_86, (copy 4): p_u_195, (ref 5): v_u_9, (copy 6): p_u_197, (copy 7): v_u_199, (ref 8): v_u_7 ]]
        v_u_85 = v_u_15.PlayerAssignmentData:from_table(p202)
        v_u_86 = true
        if p200 == true then
            p_u_195._player_blob_manager:do_sync(function() --[[ Line: 563 ]]
                --[[ Upvalues: (ref 1): p_u_195, (ref 2): v_u_9, (copy 3): p_u_201, (ref 4): p_u_197, (ref 5): v_u_199, (ref 6): v_u_7 ]]
                p_u_195._menus:push_menu(v_u_9:new(p_u_195, p_u_195._spui, p_u_195._menus):set_text("Assignment Complete!", string.format("You earned...\n\n%s\n\n%s", p_u_201, "Assign minis with higher total power to earn more rewards!")))
                if p_u_197 then
                    p_u_197()
                end;
                p_u_195._menus:remove_menu(v_u_199)
                p_u_195._sfx_manager:play_sfx(v_u_7.SFX_ACQUIRE)
            end)
        else
            p_u_195._menus:push_menu(v_u_9:new(p_u_195, p_u_195._spui, p_u_195._menus):set_text("Error", p_u_201))
            if p_u_197 then
                p_u_197()
            end;
            p_u_195._menus:remove_menu(v_u_199)
        end;
    end)
    p_u_195._evt:fire_event_to_server(v_u_8.EVT_PetAssignment_ClaimRewards_Client, p196)
end;
local l_Type2_0 = v_u_15.AssignmentType.Type2
v_u_80.create_new_assignment = function(_, p_u_203, p_u_204) --[[ Name: create_new_assignment ]] --[[ Line: 584 ]]
    --[[ Upvalues: (copy 1): v_u_9, (ref 2): v_u_86, (ref 3): v_u_85, (copy 4): v_u_15, (copy 5): v_u_11, (copy 6): v_u_2, (copy 7): v_u_10, (copy 8): v_u_14, (copy 9): v_u_3, (ref 10): l_Type2_0, (copy 11): v_u_21, (copy 12): v_u_16, (copy 13): v_u_17, (copy 14): v_u_18, (copy 15): v_u_20, (ref 16): v_u_23, (copy 17): v_u_1, (copy 18): v_u_80, (copy 19): v_u_7 ]]
    local function f_error_popup(p205) --[[ Name: error_popup ]] --[[ Line: 585 ]]
        --[[ Upvalues: (copy 1): p_u_203, (ref 2): v_u_9 ]]
        p_u_203._menus:push_menu(v_u_9:new(p_u_203, p_u_203._spui, p_u_203._menus):set_text("Error", p205))
    end;
    if v_u_86 ~= true then
        return f_error_popup("cached data not loaded");
    end;
    if v_u_85:get_assignment_datas():count() >= v_u_15:get_max_player_assignments() then
        return f_error_popup("Max assignments reached");
    end;
    local v206, v_u_207, _, _ = v_u_11:is_event_active(p_u_203._player_blob_manager:get_day_event_list())
    if v206 ~= true then
        return f_error_popup("Event is not active");
    end;
    local v_u_208 = v_u_11:get_event_info(v_u_207):get_songs_set()
    v_u_2:remove_if(v_u_208, function(_, p209) --[[ Line: 596 ]]
        --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_14 ]]
        return v_u_10:singleton():key_get_audiomod(p209) ~= v_u_14.Normal;
    end)
    v_u_3:for_each(v_u_85:get_assignment_datas(), function(p210) --[[ Line: 599 ]]
        --[[ Upvalues: (copy 1): v_u_208 ]]
        v_u_208:remove(p210:get_song_key())
    end)
    if v_u_208:count() == 0 then
        return f_error_popup("No available songs");
    end;
    local v_u_211 = p_u_203._player_blob_manager:get_player_blob()
    local v212 = v_u_208:key_list():random()
    p_u_203._bgm_manager:preview_songkey(v212)
    local v_u_213 = v_u_15.AssignmentData:new(l_Type2_0, v212)
    local function f_get_neu_assignment_owned_pet_for_index(p214) --[[ Name: get_neu_assignment_owned_pet_for_index ]] --[[ Line: 619 ]]
        --[[ Upvalues: (copy 1): v_u_213, (ref 2): v_u_21, (copy 3): v_u_211 ]]
        local v215 = v_u_213:get_pet_owned_id_set():key_list()
        v215:sort(function(p216, p217) --[[ Line: 621 ]]
            return p216 < p217;
        end)
        if v215:count() < p214 then
            return nil, 1;
        end;
        local v218 = v215:get(p214)
        return v_u_21:playerblob_get_pet_ownedid_ownedpet(v_u_211, v218), v218;
    end;
    local function f_neu_assignment_data_get_total_gear_power() --[[ Name: neu_assignment_data_get_total_gear_power ]] --[[ Line: 629 ]]
        --[[ Upvalues: (copy 1): v_u_213, (ref 2): v_u_16, (ref 3): v_u_21, (copy 4): v_u_211, (ref 5): v_u_17, (ref 6): v_u_18 ]]
        local v219 = 0
        for v220, _ in v_u_213:get_pet_owned_id_set():key_itr() do
            local v221 = v_u_16:statsdict_base()
            v_u_21:playerblob_apply_pet_ownedid_statsdict(v_u_211, v220, v221)
            v219 = v219 + v_u_17:statsdict_get_gear_power(v221, true, v_u_18:songkey_get_color_list(v_u_213:get_song_key()))
        end;
        return v219;
    end;
    local function f_opt_show_pet_of_index(p222, _, p223, p224, _, p225) --[[ Name: opt_show_pet_of_index ]] --[[ Line: 648 ]]
        --[[ Upvalues: (copy 1): f_get_neu_assignment_owned_pet_for_index, (ref 2): v_u_21, (ref 3): v_u_20, (ref 4): v_u_16, (copy 5): v_u_211, (ref 6): v_u_17, (ref 7): v_u_18, (copy 8): v_u_213 ]]
        local v226, v227 = f_get_neu_assignment_owned_pet_for_index(p222)
        if v226 then
            local v228 = v_u_21:ownedpet_get_petid(v226)
            p223.Text = v_u_20:singleton():get_name_for_petid(v228)
            p224.Image = v_u_20:singleton():get_data_for_petid(v228):get_icon()
            local v229 = v_u_16:statsdict_base()
            v_u_21:playerblob_apply_pet_ownedid_statsdict(v_u_211, v227, v229)
            p225:get_description_display().Text = string.format("[Power: %d] Level: %d", v_u_17:statsdict_get_gear_power(v229, true, v_u_18:songkey_get_color_list(v_u_213:get_song_key())), v_u_21:ownedpet_get_level(v226))
            p225:set_select_button_text("Remove")
            p225:set_select_button_enabled(true)
        end;
    end;
    local v_u_230 = nil
    v_u_230 = p_u_203._menus:push_menu(v_u_23:new(p_u_203, p_u_203._spui, p_u_203._menus, function(p231) --[[ Line: 669 ]]
        --[[ Upvalues: (copy 1): v_u_213, (copy 2): f_neu_assignment_data_get_total_gear_power ]]
        p231:set_header_text(string.format("New Training Assignment"))
        p231:get_element_list():push_back(1)
        p231:get_element_list():push_back(2)
        p231:get_element_list():push_back(3)
        if v_u_213:get_pet_owned_id_set():count() > 0 then
            p231:get_element_list():push_back(4)
            if v_u_213:get_pet_owned_id_set():count() > 1 then
                p231:get_element_list():push_back(5)
            end;
            if v_u_213:get_pet_owned_id_set():count() > 2 then
                p231:get_element_list():push_back(6)
            end;
        end;
        p231:get_element_list():push_back(7)
        p231:set_sub_text(string.format("Total Power: %d", (f_neu_assignment_data_get_total_gear_power())))
    end, function(p232, p233, p234, p235, p236) --[[ Line: 688 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_213, (ref 3): v_u_10, (ref 4): v_u_18, (ref 5): v_u_15, (copy 6): f_opt_show_pet_of_index, (ref 7): v_u_21 ]]
        if p232 == 1 then
            p233.Text = "Send Assignment"
            p234.Image = v_u_1:get_double_arrow_icon_assetid()
            p236:set_select_button_text("Send!")
            if v_u_213:get_pet_owned_id_set():count() > 0 then
                p236:get_description_display().Text = "Send out your minis on this assignment!"
                p236:set_select_button_enabled(true)
            else
                p236:get_description_display().Text = "Assign at least one mini to be able to send out this assignment."
                p236:set_select_button_enabled(false)
            end;
        elseif p232 == 2 then
            p233.Text = string.format("Song: %s", v_u_10:singleton():get_title_for_key(v_u_213:get_song_key()))
            p234.Image = v_u_10:singleton():get_coverimage_assetid_for_key(v_u_213:get_song_key())
            p236:get_description_display().Text = string.format("Elements: %s", v_u_18:songkey_get_elements_string(v_u_213:get_song_key()))
            p236:set_select_button_text("Select")
            p236:set_select_button_enabled(true)
            return;
        elseif p232 == 3 then
            p233.Text = string.format("Duration: %s", v_u_15:assignment_type_to_string(v_u_213:get_assignment_type()))
            p234.Image = v_u_1:important_assetid()
            p236:get_description_display().Text = "Select assignment duration"
            p236:set_select_button_text("Select")
            p236:set_select_button_enabled(true)
            return;
        elseif p232 == 4 then
            f_opt_show_pet_of_index(1, p232, p233, p234, p235, p236)
            return;
        elseif p232 == 5 then
            f_opt_show_pet_of_index(2, p232, p233, p234, p235, p236)
            return;
        elseif p232 == 6 then
            f_opt_show_pet_of_index(3, p232, p233, p234, p235, p236)
        elseif p232 == 7 then
            p233.Text = string.format("Add Mini  (%d/%d)", v_u_213:get_pet_owned_id_set():count(), v_u_15:get_max_pets_in_assignment())
            p234.Image = v_u_21:get_pet_icon()
            p236:set_select_button_text("Add")
            p236:get_description_display().Text = string.format("Add a mini to this assignment")
            if v_u_213:get_pet_owned_id_set():count() < v_u_15:get_max_pets_in_assignment() then
                p236:set_select_button_enabled(true)
                return;
            end;
            p236:set_select_button_enabled(false)
        end;
    end, function(p237) --[[ Line: 744 ]]
        --[[ Upvalues: (copy 1): v_u_213, (ref 2): v_u_21, (copy 3): v_u_211, (ref 4): v_u_20, (ref 5): v_u_10, (ref 6): v_u_15, (copy 7): f_neu_assignment_data_get_total_gear_power, (copy 8): p_u_203, (ref 9): v_u_9, (ref 10): v_u_80, (ref 11): v_u_230, (copy 12): p_u_204, (ref 13): v_u_7, (copy 14): v_u_208, (ref 15): l_Type2_0, (copy 16): f_get_neu_assignment_owned_pet_for_index, (copy 17): f_error_popup, (ref 18): v_u_2, (ref 19): v_u_3, (ref 20): v_u_85, (ref 21): v_u_18, (ref 22): v_u_16, (ref 23): v_u_17, (copy 24): v_u_207 ]]
        if p237 == 1 then
            local v238 = ""
            for v239, _ in v_u_213:get_pet_owned_id_set():key_itr() do
                local v240 = v_u_21:ownedpet_get_petid(v_u_21:playerblob_get_pet_ownedid_ownedpet(v_u_211, v239))
                if v238 ~= "" then
                    v238 = v238 .. ", "
                end;
                v238 = v238 .. v_u_20:singleton():get_name_for_petid(v240)
            end;
            p_u_203._menus:push_menu(v_u_9:new(p_u_203, p_u_203._spui, p_u_203._menus):set_text("Confirm", (string.format("Are you sure you want to send out this assignment?\nSong: %s\nDuration: %s\nMinis (%d/%d): %s\nTotal Power: %d", v_u_10:singleton():get_title_for_key(v_u_213:get_song_key()), v_u_15:assignment_type_to_string(v_u_213:get_assignment_type()), v_u_213:get_pet_owned_id_set():count(), v_u_15:get_max_pets_in_assignment(), v238, (f_neu_assignment_data_get_total_gear_power())))):set_okay_button_fn(function() --[[ Line: 765 ]]
                --[[ Upvalues: (ref 1): v_u_80, (ref 2): p_u_203, (ref 3): v_u_213, (ref 4): v_u_230, (ref 5): p_u_204, (ref 6): v_u_7 ]]
                v_u_80:send_assignment(p_u_203, v_u_213, function() --[[ Line: 766 ]]
                    --[[ Upvalues: (ref 1): p_u_203, (ref 2): v_u_230, (ref 3): p_u_204 ]]
                    p_u_203._menus:remove_menu(v_u_230)
                    p_u_204()
                end)
                p_u_203._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN_LONG)
            end))
            return;
        elseif p237 == 2 then
            v_u_80:select_song_from_set(p_u_203, v_u_208, function(p241) --[[ Line: 775 ]]
                --[[ Upvalues: (ref 1): v_u_213, (ref 2): v_u_230, (ref 3): p_u_203 ]]
                v_u_213:set_song_key(p241)
                v_u_213:get_pet_owned_id_set():clear()
                v_u_230:refresh()
                p_u_203._bgm_manager:preview_songkey(p241)
            end)
            return;
        elseif p237 == 3 then
            v_u_80:select_assignment_type(p_u_203, function(p242) --[[ Line: 783 ]]
                --[[ Upvalues: (ref 1): l_Type2_0, (ref 2): v_u_213, (ref 3): v_u_230 ]]
                l_Type2_0 = p242
                v_u_213:set_assignment_type(p242)
                v_u_230:refresh()
            end)
            return;
        elseif p237 == 4 or (p237 == 5 or p237 == 6) then
            local _, v243 = f_get_neu_assignment_owned_pet_for_index(p237 == 6 and 3 or (p237 == 5 and 2 or 1))
            v_u_213:get_pet_owned_id_set():remove(v243)
            v_u_230:refresh()
        elseif p237 == 7 then
            if v_u_213:get_pet_owned_id_set():count() >= v_u_15:get_max_pets_in_assignment() then
                return f_error_popup("Max minis for assignment.");
            end;
            local v_u_244 = v_u_2:new()
            v_u_3:for_each(v_u_85:get_assignment_datas(), function(p245) --[[ Line: 803 ]]
                --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_244 ]]
                v_u_2:for_each_key_value_sorted(p245:get_pet_owned_id_set(), function(p246) --[[ Line: 804 ]]
                    --[[ Upvalues: (ref 1): v_u_244 ]]
                    v_u_244:add_set(p246)
                end)
            end)
            local v247 = v_u_21:playerblob_get_ownedid_to_ownedpet_dict(v_u_211)
            v_u_2:remove_if(v247, function(_, p248) --[[ Line: 810 ]]
                --[[ Upvalues: (copy 1): v_u_244, (ref 2): v_u_213 ]]
                return v_u_244:contains(p248) or v_u_213:get_pet_owned_id_set():contains(p248);
            end)
            if v247:count() == 0 then
                return f_error_popup("You have no available minis that can be assigned to this song.");
            end;
            local v_u_249 = v_u_2:new():add_set_from_table_list(v_u_18:songkey_get_color_list(v_u_213:get_song_key()):get_table())
            v_u_2:remove_if(v247, function(p250, _) --[[ Line: 821 ]]
                --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_20, (copy 3): v_u_249 ]]
                local v251 = false
                for _, v252 in v_u_20:singleton():get_data_for_petid((v_u_21:ownedpet_get_petid(p250))):get_active_ranked_colors_list():key_itr() do
                    if v_u_249:contains(v252) then
                        v251 = true
                        break;
                    end;
                end;
                return v251 == false;
            end)
            if v247:count() == 0 then
                return f_error_popup("You have no minis of the elements that can be assigned to this song.");
            end;
            local v_u_253 = v_u_2:new()
            v_u_2:for_each_key_value_sorted(v247, function(p254) --[[ Line: 841 ]]
                --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_21, (ref 3): v_u_211, (ref 4): v_u_17, (ref 5): v_u_18, (ref 6): v_u_213, (copy 7): v_u_253 ]]
                local v255 = v_u_16:statsdict_base()
                v_u_21:playerblob_apply_pet_ownedid_statsdict(v_u_211, p254, v255)
                v_u_253:add(p254, (v_u_17:statsdict_get_gear_power(v255, true, v_u_18:songkey_get_color_list(v_u_213:get_song_key()))))
            end)
            local v256 = v_u_253:key_list()
            v256:sort(function(p257, p258) --[[ Line: 849 ]]
                --[[ Upvalues: (copy 1): v_u_253 ]]
                return v_u_253:get(p257) > v_u_253:get(p258);
            end)
            v_u_80:select_pet_from_list(p_u_203, v256, v_u_253, v_u_207, v_u_213:get_song_key(), function(p259) --[[ Line: 859 ]]
                --[[ Upvalues: (ref 1): v_u_213, (ref 2): v_u_230 ]]
                v_u_213:get_pet_owned_id_set():add_set(p259)
                v_u_230:refresh()
            end)
        end;
    end)):set_close_on_element_select(false):set_refresh_on_refocus(true)
end;
v_u_80.send_assignment = function(_, p_u_260, p261, p_u_262) --[[ Name: send_assignment ]] --[[ Line: 874 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_8, (ref 3): v_u_85, (copy 4): v_u_15, (ref 5): v_u_86 ]]
    local v_u_263 = p_u_260._menus:push_menu(v_u_9:new(p_u_260, p_u_260._spui, p_u_260._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
    p_u_260._evt:wait_on_event_once(v_u_8.EVT_PetAssignment_SendAssignment_Server, function(p_u_264, p_u_265, p266, p267) --[[ Line: 876 ]]
        --[[ Upvalues: (ref 1): v_u_85, (ref 2): v_u_15, (ref 3): v_u_86, (copy 4): p_u_260, (ref 5): v_u_9, (copy 6): p_u_262, (copy 7): v_u_263 ]]
        v_u_85 = v_u_15.PlayerAssignmentData:from_table(p266)
        v_u_86 = true
        local function f_finish() --[[ Name: finish ]] --[[ Line: 880 ]]
            --[[ Upvalues: (copy 1): p_u_264, (ref 2): p_u_260, (ref 3): v_u_9, (copy 4): p_u_265, (ref 5): p_u_262, (ref 6): v_u_263 ]]
            if p_u_264 ~= true then
                p_u_260._menus:push_menu(v_u_9:new(p_u_260, p_u_260._spui, p_u_260._menus):set_text("Error", p_u_265))
            end;
            if p_u_262 then
                p_u_262()
            end;
            p_u_260._menus:remove_menu(v_u_263)
        end;
        if p267 == true then
            p_u_260._player_blob_manager:do_sync(function() --[[ Line: 891 ]]
                --[[ Upvalues: (copy 1): f_finish ]]
                f_finish()
            end)
        else
            f_finish()
        end;
    end)
    p_u_260._evt:fire_event_to_server(v_u_8.EVT_PetAssignment_SendAssignment_Client, p261:to_table())
end;
return v_u_80;
