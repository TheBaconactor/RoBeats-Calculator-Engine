-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:56 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_3 = require(game.ReplicatedStorage.Lobby.UI.PlayUI.PlayUITab)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_10 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_12 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_13 = require(game.ReplicatedStorage.Lobby.UI.PlayUI.PlayUITabController_Shared)
local v_u_14 = require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_15 = require(game.ReplicatedStorage.AudioData.NewSongInfo)
local v_u_16 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_17 = require(game.ReplicatedStorage.Shared.AudioRank)
local v_u_18 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_19 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_20 = require(game.ReplicatedStorage.AudioData.SongDisplayPriorityOverride)
local v_u_21 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v22 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_23 = nil
local v_u_24 = nil
v22:require_client(function() --[[ Line: 30 ]]
    --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_24 ]]
    v_u_23 = require(game.ReplicatedStorage.Lobby.Menus.CraftSongUI)
    v_u_24 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
end)
local v25 = {}
local v_u_53 = {
    ["new"] = function(_, p_u_26, p_u_27, p_u_28, p_u_29) --[[ Name: new ]] --[[ Line: 40 ]]
        --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_10, (copy 3): v_u_14, (copy 4): v_u_11, (copy 5): v_u_8, (copy 6): v_u_15, (copy 7): v_u_16, (copy 8): v_u_12, (copy 9): v_u_9, (copy 10): v_u_17 ]]
        local v30 = {
            ["layout"] = function(_) end
        }
        local v_u_31 = nil
        local v_u_32 = nil
        local v_u_33 = nil
        local v_u_34 = nil
        local v_u_35 = nil
        local v_u_36 = nil
        local v_u_37 = nil
        local v_u_38 = nil
        local v_u_39 = nil
        local v_u_40 = nil
        local v_u_41 = v_u_7:invalid_songkey()
        v30.get_element_data = function(_) --[[ Name: get_element_data ]] --[[ Line: 53 ]]
            --[[ Upvalues: (ref 1): v_u_41 ]]
            return v_u_41;
        end;
        local function _() --[[ Name: cons ]] --[[ Line: 55 ]]
            --[[ Upvalues: (copy 1): p_u_28, (ref 2): v_u_31, (ref 3): v_u_32, (ref 4): v_u_33, (ref 5): v_u_36, (ref 6): v_u_34, (ref 7): v_u_35, (ref 8): v_u_37, (ref 9): v_u_39, (ref 10): v_u_38, (ref 11): v_u_40 ]]
            local l_Frame_0 = p_u_28.MainSurface.SurfaceGui.Frame
            v_u_31 = l_Frame_0.Icon
            v_u_32 = l_Frame_0.IconOverlay
            v_u_33 = l_Frame_0.ColorSection
            v_u_36 = l_Frame_0.SongDifficultySection.Display
            v_u_34 = l_Frame_0.Background
            v_u_35 = l_Frame_0.VIPAccessDisplay
            v_u_37 = l_Frame_0.NewDisplay
            v_u_39 = l_Frame_0.FavoriteDisplay
            v_u_38 = l_Frame_0:FindFirstChild("RankDisplay")
            if v_u_38 then
                v_u_38.Visible = false
            end;
            v_u_40 = l_Frame_0.LoadingBackground.LoadingText
        end;
        local v_u_42 = true
        v30.set_visible = function(_, p43) --[[ Name: set_visible ]] --[[ Line: 79 ]]
            --[[ Upvalues: (ref 1): v_u_42, (copy 2): p_u_29 ]]
            v_u_42 = p43
            p_u_29:set_visible(p43)
        end;
        local v_u_44 = -1
        v30.display_song = function(_, p45) --[[ Name: display_song ]] --[[ Line: 85 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_10, (ref 3): v_u_31, (ref 4): v_u_32, (ref 5): v_u_33, (ref 6): v_u_40, (ref 7): v_u_38, (ref 8): v_u_44, (copy 9): p_u_26, (ref 10): v_u_14, (ref 11): v_u_35, (ref 12): v_u_11, (ref 13): v_u_8, (ref 14): v_u_39, (ref 15): v_u_37, (ref 16): v_u_15, (ref 17): v_u_16, (ref 18): v_u_36, (ref 19): v_u_12, (ref 20): v_u_41 ]]
            if v_u_7:singleton():contains_key(p45) ~= true then
                return v_u_10:warnf("PlayUITabController_AllMySongs ListElement display_song(%s) not songkey", (tostring(p45)));
            end;
            v_u_31.Visible = true
            v_u_32.Visible = true
            v_u_33.Visible = true
            v_u_40.Text = "Loading..."
            if v_u_38 then
                v_u_38.Visible = false
                v_u_44 = -1
            end;
            local v46 = p_u_26._player_blob_manager:get_player_blob()
            if v_u_7:singleton():key_get_audiomod(p45) == v_u_14.Easy then
                v_u_35.Visible = false
            elseif v_u_11:playerblob_has_vip_for_current_day(v46, p_u_26:get_current_dayid()) then
                if v_u_8:get_song_key_owned_count_including_collection(v46, p45, p_u_26._player_blob_manager:get_cached_collection_info()) <= 0 and v_u_11:get_vip_songids_set():contains(p45) then
                    v_u_35.Visible = true
                else
                    v_u_35.Visible = false
                end;
            else
                v_u_35.Visible = false
            end;
            if v_u_35.Visible == false then
                v_u_39.Visible = p_u_26._player_blob_manager:is_songkey_favorite(p45)
            else
                v_u_39.Visible = false
            end;
            local v47 = v_u_37
            local v48 = v_u_15:songkey_is_new(p45)
            if v48 then
                v48 = v_u_16.PlayUIShowNewSong == true
            end;
            v47.Visible = v48
            v_u_36.TextColor3 = v_u_7:singleton():get_difficulty_color_for_key(p45)
            v_u_36.Text = tostring(v_u_7:singleton():get_difficulty_for_key(p45))
            v_u_7:singleton():render_coverimage_for_key(v_u_31, v_u_32, p45)
            v_u_12:render_songkey_colorsection(p45, v_u_33)
            v_u_41 = p45
        end;
        v30.display_data = function(_, p49) --[[ Name: display_data ]] --[[ Line: 132 ]]
            --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_32, (ref 3): v_u_33, (ref 4): v_u_39, (ref 5): v_u_37, (ref 6): v_u_35, (ref 7): v_u_38, (ref 8): v_u_40, (ref 9): v_u_36, (ref 10): v_u_7, (ref 11): v_u_41 ]]
            v_u_31.Visible = false
            v_u_32.Visible = false
            v_u_33.Visible = false
            v_u_39.Visible = false
            v_u_37.Visible = false
            v_u_35.Visible = false
            v_u_38.Visible = false
            if p49.ShowDifficulty == nil then
                if p49.HideDifficulty ~= nil then
                    v_u_40.Text = "Hide songs of this difficulty..."
                    v_u_36.TextColor3 = v_u_7:singleton():get_difficulty_color_for_difficulty(p49.HideDifficulty)
                    v_u_36.Text = tostring(p49.HideDifficulty)
                end;
            else
                v_u_40.Text = "Show more songs..."
                v_u_36.TextColor3 = v_u_7:singleton():get_difficulty_color_for_difficulty(p49.ShowDifficulty)
                v_u_36.Text = tostring(p49.ShowDifficulty)
            end;
            v_u_41 = p49
        end;
        v30.behaviour_update = function(_, _) --[[ Name: behaviour_update ]] --[[ Line: 153 ]]
            --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_7, (copy 3): p_u_27, (ref 4): v_u_34, (ref 5): v_u_9, (ref 6): v_u_38, (ref 7): v_u_44, (copy 8): p_u_26, (ref 9): v_u_17 ]]
            if v_u_41 == v_u_7:invalid_songkey() or v_u_41 ~= p_u_27:get_play_ui():get_info_displayed_song_key() then
                v_u_34.Image = v_u_9:get_song_container_assetid()
            else
                v_u_34.Image = v_u_9:get_song_container_selected_assetid()
            end;
            if v_u_38 and (v_u_7:singleton():contains_key(v_u_41) and v_u_44 ~= p_u_26._player_song_stats_manager:get_time_last_update()) then
                v_u_44 = p_u_26._player_song_stats_manager:get_time_last_update()
                local v50, v51 = p_u_26._player_song_stats_manager:get_best_grade_rank_value(v_u_41)
                if v51 > 0 then
                    v_u_38.Image = v_u_17:get_rank_value_icon(v50)
                    v_u_38.Visible = true
                    return;
                end;
                v_u_38.Visible = false
            end;
        end;
        local l_Frame_1 = p_u_28.MainSurface.SurfaceGui.Frame
        v_u_31 = l_Frame_1.Icon
        local _ = l_Frame_1.IconOverlay
        local _ = l_Frame_1.ColorSection
        local _ = l_Frame_1.SongDifficultySection.Display
        local _ = l_Frame_1.Background
        v_u_35 = l_Frame_1.VIPAccessDisplay
        local _ = l_Frame_1.NewDisplay
        local _ = l_Frame_1.FavoriteDisplay
        local v52 = l_Frame_1:FindFirstChild("RankDisplay")
        if v52 then
            v52.Visible = false
        end;
        local _ = l_Frame_1.LoadingBackground.LoadingText
        return v30;
    end
}
local v_u_54 = true
local v_u_55 = true
local v_u_56 = v_u_13.AudioModFilterComponent:create_filter_state()
local v_u_57 = true
local v_u_58 = false
local v_u_59 = false
local v_u_60 = v_u_2:new()
local v_u_61 = v_u_13.FilterColorComponent:create_filter_state()
v25.initial_settings_sync_update = function(_, p62) --[[ Name: initial_settings_sync_update ]] --[[ Line: 185 ]]
    --[[ Upvalues: (ref 1): v_u_59, (copy 2): v_u_19 ]]
    v_u_59 = p62._player_settings_manager:get_key(v_u_19.Key.ShowAllSongs)
end;
v25.new = function(_, p_u_63, p_u_64, p_u_65, p_u_66, p_u_67, p_u_68) --[[ Name: new ]] --[[ Line: 189 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_53, (copy 4): v_u_5, (copy 5): v_u_4, (copy 6): v_u_6, (copy 7): v_u_7, (ref 8): v_u_54, (ref 9): v_u_55, (ref 10): v_u_58, (copy 11): v_u_18, (ref 12): v_u_59, (copy 13): v_u_13, (copy 14): v_u_56, (copy 15): v_u_61, (copy 16): v_u_19, (copy 17): v_u_60, (ref 18): v_u_24, (copy 19): v_u_10, (copy 20): v_u_2, (ref 21): v_u_57, (copy 22): v_u_9, (copy 23): v_u_14, (copy 24): v_u_8, (copy 25): v_u_21, (copy 26): v_u_11, (copy 27): v_u_16, (copy 28): v_u_20, (copy 29): v_u_15 ]]
    local v_u_69 = v_u_3.ControllerBase:new()
    local v_u_70 = v_u_1:new()
    local v_u_71 = v_u_1:new()
    local v_u_72 = nil
    local v_u_73 = nil
    local v_u_74 = nil
    local v_u_75 = nil
    local v_u_76 = nil
    local v_u_77 = nil
    local v_u_78 = nil
    local v_u_79 = nil
    local v_u_80 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 204 ]]
        --[[ Upvalues: (copy 1): p_u_65, (ref 2): v_u_1, (ref 3): v_u_53, (copy 4): p_u_63, (copy 5): v_u_69, (copy 6): p_u_64, (ref 7): v_u_5, (ref 8): v_u_4, (ref 9): v_u_6, (ref 10): v_u_7, (copy 11): v_u_70, (ref 12): v_u_78, (copy 13): v_u_71, (ref 14): v_u_72, (ref 15): v_u_54, (ref 16): v_u_73, (ref 17): v_u_74, (ref 18): v_u_55, (ref 19): v_u_75, (ref 20): v_u_76, (ref 21): v_u_58, (ref 22): v_u_18, (ref 23): v_u_77, (ref 24): v_u_59, (ref 25): v_u_79, (ref 26): v_u_13, (ref 27): v_u_56, (ref 28): v_u_80, (ref 29): v_u_61 ]]
        local l_AllMySongsTabItems_0 = p_u_65.AllMySongsTabItems
        local l_Proto_0 = l_AllMySongsTabItems_0.Proto
        l_Proto_0.MainSurface.SurfaceGui.Enabled = true
        l_Proto_0.Parent = nil
        for v81, v82 in v_u_1:new():push_back_table_list({
            l_AllMySongsTabItems_0.Anchor1,
            l_AllMySongsTabItems_0.Anchor2,
            l_AllMySongsTabItems_0.Anchor3,
            l_AllMySongsTabItems_0.Anchor4,
            l_AllMySongsTabItems_0.Anchor5,
            l_AllMySongsTabItems_0.Anchor6,
            l_AllMySongsTabItems_0.Anchor7,
            l_AllMySongsTabItems_0.Anchor8,
            l_AllMySongsTabItems_0.Anchor9,
            l_AllMySongsTabItems_0.Anchor10,
            l_AllMySongsTabItems_0.Anchor11,
            l_AllMySongsTabItems_0.Anchor12
        }):key_itr() do
            v82.Parent = nil
            local v83 = l_Proto_0:Clone()
            v83.Name = string.format("itr_obj(%d)", v81)
            v83.Parent = l_AllMySongsTabItems_0
            v83:SetPrimaryPartCFrame(v82.CFrame)
            local v_u_84 = nil
            v_u_84 = v_u_53:new(p_u_63, v_u_69, v83, p_u_64:add_cycle_element(p_u_63, 1, v_u_5:new(v_u_4:new(p_u_64, p_u_65.PrimaryPart, v83.PrimaryPart), p_u_63._spui, function() --[[ Line: 242 ]]
                --[[ Upvalues: (ref 1): p_u_63, (ref 2): v_u_6, (ref 3): v_u_84, (ref 4): v_u_7, (ref 5): v_u_69 ]]
                p_u_63._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                local v85 = v_u_84:get_element_data()
                if v_u_7:singleton():contains_key(v85) then
                    v_u_69:on_songkey_pressed(v85)
                else
                    v_u_69:on_data_table_pressed(v85)
                end;
            end)):set_auto_zoffset_behaviour(true):set_unselected_zoffset(500 + v81 * 10))
            v_u_70:push_back(v_u_84)
            v_u_84:set_visible(false)
        end;
        v_u_78 = p_u_64:add_cycle_element(p_u_63, 1, v_u_5:new(v_u_4:new(p_u_64, p_u_65.PrimaryPart, l_AllMySongsTabItems_0.PlayButtonSurface), p_u_63._spui, function() --[[ Line: 260 ]]
            --[[ Upvalues: (ref 1): p_u_63, (ref 2): v_u_6, (ref 3): v_u_69 ]]
            p_u_63._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            v_u_69:play_button_pressed()
        end)):set_auto_zoffset_behaviour(true):set_passive_anim(true)
        l_AllMySongsTabItems_0.PlayButtonSurface.SurfaceGui.Enabled = true
        v_u_78:set_visible(false)
        local function f_create_button_toggle(p86, p_u_87, p88) --[[ Name: create_button_toggle ]] --[[ Line: 268 ]]
            --[[ Upvalues: (copy 1): l_AllMySongsTabItems_0, (ref 2): p_u_64, (ref 3): p_u_63, (ref 4): v_u_5, (ref 5): v_u_4, (ref 6): p_u_65, (ref 7): v_u_6, (ref 8): v_u_69, (ref 9): v_u_71 ]]
            local v_u_89 = p88 == nil and true or p88
            local v90 = p86:Clone()
            v90.Parent = l_AllMySongsTabItems_0
            local v91 = p_u_64:add_cycle_element(p_u_63, 1, v_u_5:new(v_u_4:new(p_u_64, p_u_65.PrimaryPart, v90), p_u_63._spui, function() --[[ Line: 278 ]]
                --[[ Upvalues: (ref 1): p_u_63, (ref 2): v_u_6, (copy 3): p_u_87, (ref 4): v_u_89, (ref 5): v_u_69, (ref 6): p_u_64 ]]
                p_u_63._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
                p_u_87()
                if v_u_89 then
                    v_u_69:update_filter_buttons()
                    p_u_64:reset_page()
                    p_u_64:refresh_current_page()
                end;
            end)):set_auto_zoffset_behaviour(true)
            local v92 = v_u_5:button_bind_anim_toggle(v91, function() --[[ Line: 288 ]]
                --[[ Upvalues: (ref 1): p_u_64 ]]
                return p_u_64:get_alpha();
            end)
            v_u_71:push_back(v91)
            return v92;
        end;
        v_u_72 = f_create_button_toggle(p_u_65.FilterButtonProtos.FilterDifficultyButton, function() --[[ Line: 293 ]]
            --[[ Upvalues: (ref 1): v_u_54 ]]
            v_u_54 = true
        end)
        v_u_73 = f_create_button_toggle(p_u_65.FilterButtonProtos.FilterAlphabeticalButton, function() --[[ Line: 296 ]]
            --[[ Upvalues: (ref 1): v_u_54 ]]
            v_u_54 = false
        end)
        v_u_74 = f_create_button_toggle(p_u_65.FilterButtonProtos.FilterAscendingButton, function() --[[ Line: 299 ]]
            --[[ Upvalues: (ref 1): v_u_55 ]]
            v_u_55 = true
        end)
        v_u_75 = f_create_button_toggle(p_u_65.FilterButtonProtos.FilterDescendingButton, function() --[[ Line: 302 ]]
            --[[ Upvalues: (ref 1): v_u_55 ]]
            v_u_55 = false
        end)
        v_u_76 = f_create_button_toggle(p_u_65.FilterButtonProtos.FavoriteFilterButton, function() --[[ Line: 308 ]]
            --[[ Upvalues: (ref 1): v_u_58, (ref 2): p_u_63, (ref 3): v_u_18 ]]
            v_u_58 = not v_u_58
            if v_u_58 and p_u_63._player_blob_manager:is_favorite_data_loaded() ~= true then
                local v_u_93 = v_u_18:new(p_u_63, p_u_63._spui, p_u_63._menus):set_text("Loading...", "Loading favorite data...")
                p_u_63._menus:push_menu(v_u_93)
                v_u_93:set_update_fn(function() --[[ Line: 313 ]]
                    --[[ Upvalues: (ref 1): p_u_63, (copy 2): v_u_93 ]]
                    if p_u_63._player_blob_manager:is_favorite_data_loaded() == true then
                        p_u_63._menus:remove_menu(v_u_93)
                    end;
                end)
            end;
        end)
        v_u_77 = f_create_button_toggle(p_u_65.FilterButtonProtos.ShowAllSongsButton, function() --[[ Line: 320 ]]
            --[[ Upvalues: (ref 1): v_u_59 ]]
            v_u_59 = not v_u_59
        end)
        v_u_79 = v_u_13.AudioModFilterComponent:create_audiomod_filter_buttons(p_u_63, p_u_64, p_u_65.PrimaryPart, v_u_56, l_AllMySongsTabItems_0, p_u_65.FilterButtonProtos.EasyModeButton, p_u_65.FilterButtonProtos.NormalModeButton, p_u_65.FilterButtonProtos.HardModeButton, function(p94) --[[ Line: 333 ]]
            --[[ Upvalues: (ref 1): v_u_71 ]]
            v_u_71:push_back(p94)
        end, function() end)
        v_u_80 = v_u_13.FilterColorComponent:create_filter_button(p_u_63, p_u_64, p_u_65, p_u_65.FilterButtonProtos.ColorFilterButton, v_u_61, function(p95) --[[ Line: 346 ]]
            --[[ Upvalues: (ref 1): v_u_71 ]]
            v_u_71:push_back(p95)
        end, function() end)
        v_u_69:update_filter_buttons()
    end;
    v_u_69.on_clear_filter = function(p96) --[[ Name: on_clear_filter ]] --[[ Line: 355 ]]
        --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_56, (ref 3): v_u_79, (ref 4): v_u_58, (ref 5): v_u_59, (copy 6): p_u_63, (ref 7): v_u_19, (ref 8): v_u_60, (ref 9): v_u_61, (ref 10): v_u_80 ]]
        v_u_13.AudioModFilterComponent:reset_filter_state(v_u_56)
        v_u_79:update_toggle_state()
        v_u_58 = false
        v_u_59 = p_u_63._player_settings_manager:get_key(v_u_19.Key.ShowAllSongs)
        v_u_60:clear()
        v_u_13.FilterColorComponent:reset_filter_state(v_u_61)
        v_u_80:update_state()
        p96:update_filter_buttons()
    end;
    v_u_69.update_filter_buttons = function(_) --[[ Name: update_filter_buttons ]] --[[ Line: 369 ]]
        --[[ Upvalues: (ref 1): v_u_72, (ref 2): v_u_54, (ref 3): v_u_73, (ref 4): v_u_74, (ref 5): v_u_55, (ref 6): v_u_75, (ref 7): v_u_76, (ref 8): v_u_58, (ref 9): v_u_77, (ref 10): v_u_59, (ref 11): v_u_80 ]]
        v_u_72:set_toggle(v_u_54)
        v_u_73:set_toggle(not v_u_54)
        v_u_74:set_toggle(v_u_55)
        v_u_75:set_toggle(not v_u_55)
        v_u_76:set_toggle(v_u_58)
        v_u_77:set_toggle(v_u_59)
        v_u_80:update_state()
    end;
    v_u_69.on_songkey_pressed = function(p97, p98) --[[ Name: on_songkey_pressed ]] --[[ Line: 383 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_78, (copy 3): p_u_64 ]]
        if v_u_7:singleton():contains_key(p98) == true then
            p_u_64:show_info_for_songkey(p98)
            p_u_64:play_preview_for_songkey(p98)
            p97:update_play_button()
        else
            v_u_78:set_visible(false)
        end;
    end;
    v_u_69.play_button_pressed = function(_) --[[ Name: play_button_pressed ]] --[[ Line: 393 ]]
        --[[ Upvalues: (ref 1): v_u_7, (copy 2): p_u_64, (copy 3): p_u_67, (copy 4): p_u_63, (ref 5): v_u_24, (ref 6): v_u_10 ]]
        if v_u_7:singleton():contains_key(p_u_64:get_info_displayed_song_key()) then
            if p_u_67 then
                p_u_67(p_u_64:get_info_displayed_song_key())
            else
                p_u_64:set_loading(true)
                p_u_63._menus:push_menu(v_u_24:new(p_u_63, p_u_63._spui, p_u_63._menus, p_u_64:get_info_displayed_song_key(), nil))
            end;
        else
            v_u_10:puts("PlayUITabController_AllMySongs:play_button_pressed invalid(%s)", (tostring(p_u_64:get_info_displayed_song_key())))
            return;
        end;
    end;
    local v_u_99 = 0
    v_u_69.get_max_difficulty = function(_) --[[ Name: get_max_difficulty ]] --[[ Line: 410 ]]
        --[[ Upvalues: (ref 1): v_u_99 ]]
        return v_u_99;
    end;
    local v_u_100 = v_u_2:new()
    v_u_69.get_songkey_set = function(_) --[[ Name: get_songkey_set ]] --[[ Line: 412 ]]
        --[[ Upvalues: (copy 1): v_u_100 ]]
        return v_u_100;
    end;
    v_u_69.on_filter_change_difficulty = function(_, _) --[[ Name: on_filter_change_difficulty ]] --[[ Line: 414 ]]
        --[[ Upvalues: (ref 1): v_u_57 ]]
        v_u_57 = false
    end;
    local function _() --[[ Name: get_show_expanded_difficulties_key ]] --[[ Line: 419 ]]
        --[[ Upvalues: (ref 1): v_u_60, (ref 2): v_u_1, (ref 3): v_u_9 ]]
        local v101 = v_u_60:key_list()
        v_u_1:sort_fast(v101, function(p102, p103) --[[ Line: 421 ]]
            return p102 < p103;
        end)
        return v_u_9:table_to_string(v101:get_table());
    end;
    local v_u_104 = nil
    local v_u_105 = ""
    local v_u_106 = 0
    v_u_69.get_song_list = function(_) --[[ Name: get_song_list ]] --[[ Line: 428 ]]
        --[[ Upvalues: (copy 1): p_u_64, (ref 2): v_u_80, (ref 3): v_u_54, (ref 4): v_u_55, (ref 5): v_u_57, (ref 6): v_u_58, (ref 7): v_u_59, (ref 8): v_u_56, (ref 9): v_u_14, (ref 10): v_u_60, (ref 11): v_u_1, (ref 12): v_u_9, (ref 13): v_u_104, (ref 14): v_u_105, (ref 15): v_u_106, (copy 16): p_u_63, (ref 17): v_u_7, (ref 18): v_u_99, (copy 19): v_u_100, (ref 20): v_u_8, (ref 21): v_u_21, (ref 22): v_u_11, (copy 23): p_u_68, (ref 24): v_u_16, (copy 25): p_u_66, (ref 26): v_u_20, (ref 27): v_u_15, (ref 28): v_u_2, (copy 29): v_u_70 ]]
        local v_u_107 = string.lower(p_u_64:get_filter_search_name())
        local v_u_108 = string.lower(p_u_64:get_filter_artist_name())
        local v_u_109 = p_u_64:get_filter_search_difficulty()
        local v110 = v_u_80:get_filter_string()
        local l_format_0 = string.format
        local v111 = tostring(v_u_54)
        local v112 = tostring(v_u_55)
        local v113 = tostring(v_u_57)
        local v114 = tostring(v_u_58)
        local v115 = tostring(v_u_59)
        local v116 = tostring(v_u_56:get(v_u_14.Normal))
        local v117 = tostring(v_u_56:get(v_u_14.Hard))
        local v118 = tostring(v_u_56:get(v_u_14.Easy))
        local v119 = v_u_60:key_list()
        v_u_1:sort_fast(v119, function(p120, p121) --[[ Line: 421 ]]
            return p120 < p121;
        end)
        local v122 = l_format_0("a(%s) b(%s) c(%d) d(%s) e(%s) f(%s) g(%s) h(%s) i(%s) j(%s) k(%s) l(%s) m(%s)", v_u_107, v_u_108, v_u_109, v111, v112, v113, v114, v115, v116, v117, v118, v_u_9:table_to_string(v119:get_table()), v110)
        if v_u_104 and (v_u_105 == v122 and v_u_106 == p_u_63._player_blob_manager:get_synced_time()) then
            return v_u_104;
        end;
        v_u_9:profilebegin("get_song_list")
        local v_u_123 = v_u_7:singleton()
        v_u_99 = 0
        v_u_100:clear()
        v_u_9:profilebegin("song_inventory_set")
        local v124 = p_u_63._player_blob_manager:get_player_blob()
        local v125 = v_u_8:song_inventory_songids_set(v124)
        v_u_21:playerblob_add_collection_songkeys_to_set(v124, v125, p_u_63._player_blob_manager:get_cached_collection_info())
        if v_u_11:playerblob_has_vip_for_current_day(v124, p_u_63:get_current_dayid()) then
            for v126, _ in v_u_11:get_vip_songids_set():key_itr() do
                v125:add_set(v126)
            end;
        end;
        for v127, _ in v_u_123:get_easymode_keys_set():key_itr() do
            v125:add_set(v127)
        end;
        if p_u_68 ~= nil then
            p_u_68(v125)
        end;
        v_u_9:profileend()
        if v_u_16.TesterStatusShowAllSongs == true and v_u_8:is_tester_status(v124) == true then
            for _, v128 in v_u_7:singleton():all_keys():key_itr() do
                v125:add_set(v128)
            end;
        end;
        local v_u_129, v_u_130, v_u_131 = v_u_80:get_filter_colors()
        local v132 = v125:key_list()
        v_u_9:profilebegin("splist_filter")
        local v_u_135 = v_u_9:splist_filter(v132, function(p133) --[[ Line: 487 ]]
            --[[ Upvalues: (ref 1): v_u_100, (copy 2): v_u_107, (copy 3): v_u_123, (copy 4): v_u_108, (copy 5): v_u_109, (ref 6): v_u_56, (copy 7): v_u_129, (ref 8): v_u_80, (copy 9): v_u_130, (copy 10): v_u_131, (ref 11): v_u_99, (ref 12): p_u_66 ]]
            v_u_100:add_set(p133)
            if #v_u_107 > 0 and string.find(v_u_123:get_title_lower_for_key(p133), v_u_107, 1, true) == nil then
                return false;
            end;
            if #v_u_108 > 0 and string.find(v_u_123:get_artist_lower_for_key(p133), v_u_108, 1, true) == nil then
                return false;
            end;
            local v134 = v_u_123:get_difficulty_for_key(p133)
            if v134 < v_u_109 then
                return false;
            end;
            if v_u_56:get(v_u_123:key_get_audiomod(p133)) ~= true then
                return false;
            end;
            if v_u_129 and v_u_80:songkey_test_filter_colors(p133, v_u_130, v_u_131) ~= true then
                return false;
            end;
            v_u_99 = math.max(v_u_99, v134)
            return not p_u_66 and true or p_u_66(p133);
        end)
        v_u_9:profileend()
        local function _(p136, p137) --[[ Name: order_songkey_name ]] --[[ Line: 526 ]]
            --[[ Upvalues: (ref 1): v_u_55, (copy 2): v_u_123 ]]
            if v_u_55 then
                return v_u_123:get_title_lower_for_key(p137) > v_u_123:get_title_lower_for_key(p136);
            else
                return v_u_123:get_title_lower_for_key(p137) < v_u_123:get_title_lower_for_key(p136);
            end;
        end;
        local function _(p138, p139) --[[ Name: order_songkey_id ]] --[[ Line: 534 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_55 ]]
            if v_u_20:contains(p138) then
                p138 = v_u_20:get(p138)
            end;
            if v_u_20:contains(p139) then
                p139 = v_u_20:get(p139)
            end;
            if v_u_55 then
                return p139 < p138;
            else
                return p138 < p139;
            end;
        end;
        v_u_9:profilebegin("sort_fn")
        local function _(p140, p141) --[[ Line: 545 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_55 ]]
            if v_u_20:contains(p140) then
                p140 = v_u_20:get(p140)
            end;
            if v_u_20:contains(p141) then
                p141 = v_u_20:get(p141)
            end;
            if v_u_55 then
                return p141 < p140;
            else
                return p140 < p141;
            end;
        end;
        if v_u_54 then
            if v_u_55 then
                v_u_1:sort_fast(v_u_135, function(p142, p143) --[[ Line: 548 ]]
                    --[[ Upvalues: (copy 1): v_u_123, (ref 2): v_u_20, (ref 3): v_u_55 ]]
                    local v144 = v_u_123:get_difficulty_for_key(p142)
                    local v145 = v_u_123:get_difficulty_for_key(p143)
                    if v144 == v145 then
                        if v_u_20:contains(p142) then
                            p142 = v_u_20:get(p142)
                        end;
                        if v_u_20:contains(p143) then
                            p143 = v_u_20:get(p143)
                        end;
                        if v_u_55 then
                            return p143 < p142;
                        else
                            return p142 < p143;
                        end;
                    else
                        return v144 < v145;
                    end;
                end)
            else
                v_u_1:sort_fast(v_u_135, function(p146, p147) --[[ Line: 556 ]]
                    --[[ Upvalues: (copy 1): v_u_123, (ref 2): v_u_20, (ref 3): v_u_55 ]]
                    local v148 = v_u_123:get_difficulty_for_key(p146)
                    local v149 = v_u_123:get_difficulty_for_key(p147)
                    if v148 == v149 then
                        if v_u_20:contains(p146) then
                            p146 = v_u_20:get(p146)
                        end;
                        if v_u_20:contains(p147) then
                            p147 = v_u_20:get(p147)
                        end;
                        if v_u_55 then
                            return p147 < p146;
                        else
                            return p146 < p147;
                        end;
                    else
                        return v149 < v148;
                    end;
                end)
            end;
        else
            v_u_1:sort_fast(v_u_135, function(p150, p151) --[[ Line: 565 ]]
                --[[ Upvalues: (ref 1): v_u_55, (copy 2): v_u_123 ]]
                if v_u_55 then
                    return v_u_123:get_title_lower_for_key(p151) > v_u_123:get_title_lower_for_key(p150);
                else
                    return v_u_123:get_title_lower_for_key(p151) < v_u_123:get_title_lower_for_key(p150);
                end;
            end)
        end;
        v_u_9:profileend()
        v_u_9:profilebegin("_display_new_modes_first")
        if v_u_57 and v_u_58 ~= true then
            local v152 = v_u_1:new()
            for _, v153 in v_u_135:key_itr() do
                if v_u_15:songkey_is_new(v153) and v_u_16.PlayUIShowNewSong == true then
                    v152:push_back(v153)
                end;
            end;
            local v_u_154 = 12 - v152:count() % 12
            local function f_get_list_remove_at_indices() --[[ Name: get_list_remove_at_indices ]] --[[ Line: 584 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_135, (ref 3): v_u_15, (ref 4): v_u_16, (copy 5): v_u_154 ]]
                local v155 = v_u_1:new()
                for v156, v157 in v_u_135:key_itr() do
                    if v_u_15:songkey_is_new(v157) and v_u_16.PlayUIShowNewSong == true then
                        v155:push_back(v156)
                    end;
                    if v_u_154 <= v156 then
                        break;
                    end;
                end;
                return v155;
            end;
            for _ = 1, 25 do
                local v158 = f_get_list_remove_at_indices()
                if v158:count() == 0 then
                    break;
                end;
                for v159 = v158:count(), 1, -1 do
                    v_u_135:remove_at(v158:get(v159))
                end;
            end;
            for v160 = v152:count(), 1, -1 do
                v_u_135:push_front((v152:get(v160)))
            end;
        end;
        v_u_9:profileend()
        if v_u_58 == true then
            v_u_135:remove_if(function(p161) --[[ Line: 614 ]]
                --[[ Upvalues: (ref 1): p_u_63 ]]
                return p_u_63._player_blob_manager:is_songkey_favorite(p161) ~= true;
            end)
        end;
        if v_u_135:count() > 0 then
            local v162 = v_u_123:get_all_modes_of_songkey((v_u_135:get(1)))
            local v163 = true
            for _, v164 in v_u_135:key_itr() do
                if v162:contains(v164) ~= true then
                    v163 = false
                    break;
                end;
            end;
            if v163 ~= true then
                v_u_135:remove_if(function(p165) --[[ Line: 633 ]]
                    --[[ Upvalues: (copy 1): v_u_123, (ref 2): v_u_7 ]]
                    return v_u_123:get_songkey_priority(p165) == v_u_7.SongPriority.Hidden;
                end)
            end;
        end;
        local v166
        if v_u_54 and v_u_59 ~= true then
            local v167 = v_u_2:new()
            v166 = v_u_1:new()
            local v168 = v_u_70:count()
            local v169 = v168 - 1
            local v170 = v168 - 2
            for v171 = 1, v_u_135:count() do
                local v172 = v166:count()
                local v173 = v_u_135:get(v171)
                local v174 = v_u_123:get_difficulty_for_key(v173)
                if v_u_60:contains(v174) ~= true and v167:contains(v174) ~= true then
                    local v175
                    if v172 % v168 == v169 and v170 < v172 then
                        v175 = v_u_123:get_difficulty_for_key(v166:get(v172 - v170)) == v174
                    else
                        v175 = false
                    end;
                    if v175 then
                        for v176 = v172 - v170, v172 do
                            if v_u_123:get_difficulty_for_key(v166:get(v176)) ~= v174 then
                                v175 = false
                                break;
                            end;
                        end;
                    end;
                    if v175 then
                        v166:push_back({
                            ["ShowDifficulty"] = v174
                        })
                        v167:add_set(v174)
                    end;
                end;
                if v167:contains(v174) ~= true then
                    v166:push_back(v173)
                end;
            end;
        else
            v166 = v_u_135
        end;
        v_u_104 = v166
        v_u_105 = v122
        v_u_106 = p_u_63._player_blob_manager:get_synced_time()
        v_u_9:profileend()
        return v166;
    end;
    v_u_69.on_data_table_pressed = function(_, p177) --[[ Name: on_data_table_pressed ]] --[[ Line: 694 ]]
        --[[ Upvalues: (ref 1): v_u_60, (copy 2): p_u_64 ]]
        if p177.ShowDifficulty == nil then
            if p177.HideDifficulty ~= nil then
                v_u_60:remove(p177.HideDifficulty)
            end;
        else
            v_u_60:add_set(p177.ShowDifficulty)
        end;
        p_u_64:refresh_current_page()
    end;
    v_u_69.songkey_selected = function(p_u_178, p179) --[[ Name: songkey_selected ]] --[[ Line: 704 ]]
        --[[ Upvalues: (ref 1): v_u_11, (copy 2): p_u_63, (copy 3): p_u_64, (ref 4): v_u_60, (ref 5): v_u_7, (copy 6): v_u_70 ]]
        local v180 = false
        if p_u_178:get_song_list():find(p179) == -1 then
            if v_u_11:playerblob_has_access_to_song(p_u_63._player_blob_manager:get_player_blob(), p179, p_u_63:get_current_dayid(), p_u_63._player_blob_manager:get_cached_collection_info()) then
                p_u_64:do_clear_filters()
                v_u_60:add_set(v_u_7:singleton():get_difficulty_for_key(p179))
                p_u_64:raise_filter_changed()
                p_u_64:refresh_current_page()
                v180 = p_u_178:get_song_list():find(p179) ~= -1 and true or v180
            end;
        else
            v180 = true
        end;
        local function f_try_select_songkey(p181) --[[ Name: try_select_songkey ]] --[[ Line: 731 ]]
            --[[ Upvalues: (ref 1): v_u_70, (ref 2): p_u_64, (copy 3): p_u_178 ]]
            local v182 = v_u_70:count()
            p_u_64:set_page(0)
            local v183 = false
            while true do
                local v184 = p_u_64:get_page()
                local v185 = p_u_178:get_song_list()
                for v186 = 1, v182 do
                    local v187 = v184 * v182 + v186
                    if v187 <= v185:count() and v185:get(v187) == p181 then
                        v183 = true
                    end;
                end;
                if v183 ~= true then
                    p_u_64:set_page(p_u_64:get_page() + 1)
                end;
                if v183 == true or p_u_64:get_page() >= p_u_178:get_page_total() then
                    if v183 == false then
                        p_u_64:set_page(0)
                    end;
                    return v183;
                end;
            end;
        end;
        if v180 then
            if f_try_select_songkey(p179) == false then
                v180 = false
            end;
            p_u_64:refresh_current_page()
        end;
        return v180;
    end;
    v_u_69.load_data = function(_, p188) --[[ Name: load_data ]] --[[ Line: 770 ]]
        p188()
    end;
    v_u_69.get_page_total = function(p189) --[[ Name: get_page_total ]] --[[ Line: 774 ]]
        --[[ Upvalues: (copy 1): v_u_70 ]]
        return math.ceil(p189:get_song_list():count() / v_u_70:count());
    end;
    v_u_69.refresh = function(p190) --[[ Name: refresh ]] --[[ Line: 778 ]]
        --[[ Upvalues: (copy 1): p_u_64, (copy 2): v_u_70, (ref 3): v_u_7 ]]
        local v191 = p_u_64:get_page()
        local v192 = p190:get_song_list()
        local v193 = p_u_64:get_info_displayed_song_key()
        local v194 = false
        for v195 = 1, v_u_70:count() do
            local v196 = v_u_70:get(v195)
            local v197 = v191 * v_u_70:count() + v195
            if v197 <= v192:count() then
                local v198 = v192:get(v197)
                if v_u_7:singleton():contains_key(v198) then
                    v196:set_visible(true)
                    v196:display_song(v198)
                    if v193 == v198 and v193 ~= v_u_7:invalid_songkey() then
                        v194 = true
                    end;
                else
                    v196:set_visible(true)
                    v196:display_data(v198)
                end;
            else
                v196:set_visible(false)
            end;
        end;
        if v194 ~= true then
            p_u_64:set_info_displayed_song_key(v_u_7:invalid_songkey())
        end;
        p190:update_play_button()
        p190:update_filter_buttons()
    end;
    v_u_69.update_play_button = function(_) --[[ Name: update_play_button ]] --[[ Line: 812 ]]
        --[[ Upvalues: (copy 1): p_u_64, (ref 2): v_u_7, (ref 3): v_u_78 ]]
        if p_u_64:get_info_displayed_song_key() == v_u_7:invalid_songkey() then
            v_u_78:set_visible(false)
        else
            v_u_78:set_visible(true)
        end;
    end;
    local v_u_199 = false
    v_u_69.set_visible = function(p200, p201) --[[ Name: set_visible ]] --[[ Line: 821 ]]
        --[[ Upvalues: (ref 1): v_u_199, (copy 2): v_u_70, (ref 3): v_u_78, (copy 4): v_u_71 ]]
        v_u_199 = p201
        for v202 = 1, v_u_70:count() do
            v_u_70:get(v202):set_visible(p201)
        end;
        if p201 then
            p200:update_play_button()
        else
            v_u_78:set_visible(false)
        end;
        for v203 = 1, v_u_71:count() do
            v_u_71:get(v203):set_visible(p201)
        end;
    end;
    v_u_69.layout = function(_) --[[ Name: layout ]] --[[ Line: 836 ]]
        --[[ Upvalues: (copy 1): v_u_70 ]]
        for v204 = 1, v_u_70:count() do
            v_u_70:get(v204):layout()
        end;
    end;
    v_u_69.behaviour_update = function(_, p205) --[[ Name: behaviour_update ]] --[[ Line: 842 ]]
        --[[ Upvalues: (copy 1): v_u_70 ]]
        for v206 = 1, v_u_70:count() do
            v_u_70:get(v206):behaviour_update(p205)
        end;
    end;
    v_u_69.get_play_ui = function(_) --[[ Name: get_play_ui ]] --[[ Line: 848 ]]
        --[[ Upvalues: (copy 1): p_u_64 ]]
        return p_u_64;
    end;
    f_cons()
    return v_u_69;
end;
return v25;
