-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:38 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_7 = require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_8 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_9 = require(game.ReplicatedStorage.Lobby.UI.GameEndV2RankPlayerDisplay)
local v_u_10 = require(game.ReplicatedStorage.Shared.AudioRank)
local v_u_11 = require(game.ReplicatedStorage.Lobby.UI.ChatUISection)
local v_u_12 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_13 = require(game.ReplicatedStorage.LocalShared.BGMManager)
local v_u_14 = require(game.ReplicatedStorage.Lobby.UI.GameEndV2RewardsSection)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_15 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_16 = require(game.ReplicatedStorage.Lobby.UI.NoteTimeGraph)
require(game.ReplicatedStorage.Shared.EventString)
require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_17 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_18 = require(game.ReplicatedStorage.Lobby.UI.GameEndV2RouletteSection)
local v_u_19 = require(game.ReplicatedStorage.Shared.MatchMode)
require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v20 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_21 = nil
local v_u_22 = nil
v20:require_client(function() --[[ Line: 33 ]]
    --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_22 ]]
    v_u_21 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
    v_u_22 = require(game.ReplicatedStorage.Lobby.UI.SongFavoriteButton)
end)
return {
    ["new"] = function(_, p_u_23, p_u_24) --[[ Name: new ]] --[[ Line: 40 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_19, (copy 4): v_u_1, (copy 5): v_u_16, (copy 6): v_u_5, (copy 7): v_u_4, (copy 8): v_u_12, (copy 9): v_u_11, (copy 10): v_u_14, (copy 11): v_u_18, (ref 12): v_u_22, (copy 13): v_u_9, (copy 14): v_u_10, (copy 15): v_u_8, (copy 16): v_u_17, (copy 17): v_u_7, (ref 18): v_u_21, (copy 19): v_u_6, (copy 20): v_u_13, (copy 21): v_u_15 ]]
        local l__spui_0 = p_u_23._spui
        local l__menus_0 = p_u_23._menus
        local v_u_25 = v_u_3:new(l__spui_0, l__menus_0)
        local v_u_26 = v_u_2:new()
        local v_u_27 = nil
        local v_u_28 = 1
        local v_u_29 = nil
        local v_u_30 = 0
        local v_u_31 = nil
        local v_u_32 = nil
        local v_u_33 = nil
        local v_u_34 = nil
        local v_u_35 = nil
        local v_u_36 = nil
        local v_u_37 = nil
        local v_u_38 = nil
        local v_u_39 = nil
        local v_u_40 = 0
        local v_u_41 = v_u_19:get_selected_mode()
        v_u_25.get_display_match_mode = function(_) --[[ Name: get_display_match_mode ]] --[[ Line: 66 ]]
            --[[ Upvalues: (ref 1): v_u_41 ]]
            return v_u_41;
        end;
        local v_u_42 = nil
        local function f_cons() --[[ Name: cons ]] --[[ Line: 70 ]]
            --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_27, (ref 3): v_u_1, (copy 4): v_u_25, (ref 5): v_u_34, (ref 6): v_u_35, (ref 7): v_u_36, (ref 8): v_u_16, (copy 9): p_u_24, (ref 10): v_u_37, (ref 11): v_u_5, (ref 12): v_u_4, (copy 13): l__spui_0, (ref 14): v_u_33, (ref 15): v_u_12, (ref 16): v_u_2, (ref 17): v_u_19, (ref 18): v_u_41, (ref 19): v_u_39, (ref 20): v_u_38, (ref 21): v_u_29, (ref 22): v_u_11, (ref 23): v_u_31, (ref 24): v_u_14, (ref 25): v_u_32, (ref 26): v_u_18, (ref 27): v_u_42, (ref 28): v_u_22, (ref 29): v_u_40 ]]
            p_u_23._input:set_mouse_visible(true)
            p_u_23._input:set_keyboard_focused_mode(false)
            p_u_23._chat:set_chat_visible(p_u_23._chat:get_stored_chat_visible())
            v_u_27 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.GameEndV2UI:Clone()
            v_u_27.Name = v_u_1:gen_name(v_u_27.Name)
            v_u_25:set_showing(true)
            v_u_25._native_size = v_u_27.PrimaryPart.Size
            v_u_25._size = v_u_25._native_size
            v_u_34 = v_u_27.MainSurface.SurfaceGui.Frame.PerformanceDisplaySection
            v_u_35 = v_u_27.MainSurface.SurfaceGui.Frame.NoteTimeGraph
            v_u_34.Visible = true
            v_u_35.Visible = false
            v_u_36 = v_u_16:new(v_u_35, p_u_24)
            v_u_37 = v_u_25:add_cycle_element(p_u_23, 1, v_u_5:new(v_u_4:new(v_u_25, v_u_27.PrimaryPart, v_u_27.BackButtonSurface), l__spui_0, function() --[[ Line: 91 ]]
                --[[ Upvalues: (ref 1): v_u_25 ]]
                v_u_25:on_close_button()
            end))
            v_u_33 = v_u_25:add_cycle_element(p_u_23, 1, v_u_5:new(v_u_4:new(v_u_25, v_u_27.PrimaryPart, v_u_27.InfoButtonSurface), l__spui_0, function() --[[ Line: 98 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_12 ]]
                p_u_23._sfx_manager:play_sfx(v_u_12.SFX_BUTTONPRESS)
            end):set_passive_anim():set_selected_rotation_amplitude(20))
            local v_u_43 = v_u_2:new():push_back_table_list({ v_u_27.MatchModeButton.SurfaceGui.Frame.ImageFront, v_u_27.MatchModeButton.SurfaceGui.Frame.ImageShadow })
            local function _() --[[ Name: update_match_mode_button_image ]] --[[ Line: 104 ]]
                --[[ Upvalues: (copy 1): v_u_43, (ref 2): v_u_19, (ref 3): v_u_41 ]]
                for _, v44 in v_u_43:key_itr() do
                    v44.Image = v_u_19:get_icon_for_mode(v_u_41)
                end;
            end;
            for _, v45 in v_u_43:key_itr() do
                v45.Image = v_u_19:get_icon_for_mode(v_u_41)
            end;
            v_u_39 = v_u_25:add_cycle_element(p_u_23, 1, v_u_5:new(v_u_4:new(v_u_25, v_u_27.PrimaryPart, v_u_27.MatchModeButton), l__spui_0, function() --[[ Line: 111 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_12, (ref 3): v_u_41, (ref 4): v_u_19, (copy 5): v_u_43, (ref 6): v_u_25 ]]
                p_u_23._sfx_manager:play_sfx(v_u_12.SFX_BUTTONPRESS)
                if v_u_41 == v_u_19.Casual then
                    v_u_41 = v_u_19.Compete
                elseif v_u_41 == v_u_19.Compete then
                    v_u_41 = v_u_19.Casual
                end;
                for _, v46 in v_u_43:key_itr() do
                    v46.Image = v_u_19:get_icon_for_mode(v_u_41)
                end;
                v_u_25:set_display_mode(false)
            end))
            v_u_38 = v_u_25:add_cycle_element(p_u_23, 1, v_u_5:new(v_u_4:new(v_u_25, v_u_27.PrimaryPart, v_u_27.PlayAgainButton), l__spui_0, function() --[[ Line: 126 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_12, (ref 3): v_u_25 ]]
                p_u_23._sfx_manager:play_sfx(v_u_12.SFX_BUTTONPRESS)
                v_u_25:on_play_again_pressed()
            end):set_passive_anim())
            if p_u_24:is_spectate() then
                v_u_38:set_visible(false)
            else
                v_u_38:set_visible(true)
            end;
            v_u_29 = v_u_11:new(p_u_23, l__spui_0, v_u_25, v_u_27.MainSurface.SurfaceGui.Frame.ChatSection.ChatTextFrameOutline.ChatTextFrame, v_u_27.MainSurface.SurfaceGui.Frame.ChatSection.ChatBarFrame)
            v_u_31 = v_u_14:new(p_u_24, p_u_23, v_u_4:new(v_u_25, v_u_27.PrimaryPart, v_u_27.RewardsSurface))
            v_u_32 = v_u_18:new(p_u_24, p_u_23, v_u_4:new(v_u_25, v_u_27.PrimaryPart, v_u_27.RewardRouletteSurface))
            v_u_42 = v_u_22:new(p_u_23, v_u_25, v_u_4:new(v_u_25, v_u_27.PrimaryPart, v_u_27.FavoriteButton), v_u_27.FavoriteButton.SurfaceGui.Button.Icon):set_fn_get_selected_songkey(function() --[[ Line: 179 ]]
                --[[ Upvalues: (ref 1): p_u_24 ]]
                return p_u_24:es_gamelocal_get_audiomanager():get_song_key();
            end):set_fn_on_favorite_updated(function() --[[ Line: 180 ]]
                --[[ Upvalues: (ref 1): v_u_25 ]]
                v_u_25:update_labels()
            end)
            v_u_25:create_elements()
            v_u_25:update_labels()
            v_u_40 = p_u_24._players:get_last_updated_time()
        end;
        v_u_25.update_reward_info = function(_, p47) --[[ Name: update_reward_info ]] --[[ Line: 187 ]]
            --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_32 ]]
            if v_u_31 ~= nil then
                v_u_31:load_reward_info(p47)
            end;
            if v_u_32 ~= nil then
                v_u_32:load_reward_info(p47)
            end;
        end;
        v_u_25.spectate_update_rewards_and_show = function(_, p48, p49) --[[ Name: spectate_update_rewards_and_show ]] --[[ Line: 196 ]]
            --[[ Upvalues: (ref 1): v_u_31 ]]
            if v_u_31 ~= nil then
                v_u_31:load_reward_info({
                    ["MatchCoinReward"] = 0,
                    ["VIPCoinBonusReward"] = 0,
                    ["NoMissReward"] = 0,
                    ["MostAccurateReward"] = 0,
                    ["PlayerCount"] = -1,
                    ["Place"] = -1,
                    ["QuitEarly"] = false,
                    ["IsSpectate"] = true,
                    ["SpectateCheerCount"] = p48,
                    ["SpectateCheerCoins"] = p49
                })
            end;
        end;
        v_u_25.create_elements = function(p50) --[[ Name: create_elements ]] --[[ Line: 215 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_27, (ref 3): v_u_9, (ref 4): v_u_26 ]]
            local v51 = v_u_2:new():push_back_table_list({
                v_u_27.Anchors.Place1,
                v_u_27.Anchors.Place2,
                v_u_27.Anchors.Place3,
                v_u_27.Anchors.Place4
            })
            local v52 = v_u_2:new():push_back_table_list({
                v_u_27.PlayerSlotProto,
                v_u_27.PlayerSlotProto:Clone(),
                v_u_27.PlayerSlotProto:Clone(),
                v_u_27.PlayerSlotProto:Clone()
            })
            for v53 = 1, 4 do
                local v54 = v_u_9:new(v52:get(v53), p50, v_u_27.PrimaryPart)
                v54:set_position(v51:get(v53).Anchor.Position)
                v_u_26:push_back(v54)
            end;
            p50:set_display_mode(true)
        end;
        v_u_25.set_display_mode = function(p55, p56) --[[ Name: set_display_mode ]] --[[ Line: 242 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): p_u_24, (ref 3): v_u_41, (ref 4): v_u_19, (ref 5): v_u_26, (ref 6): v_u_10 ]]
            local v57 = v_u_2:new()
            for v58 = 1, 4 do
                if p_u_24._players._slots:contains(v58) then
                    v57:push_back((p_u_24._players._slots:get(v58)))
                end;
            end;
            v57:sort(function(p59, p60) --[[ Line: 250 ]]
                --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_19 ]]
                if v_u_41 == v_u_19.Compete then
                    return p59._score - p60._score;
                else
                    return p59._naked_score - p60._naked_score;
                end;
            end)
            p55:set_alpha(p55:get_alpha(), true)
            for v61 = 1, 4 do
                local v62 = v_u_26:get(v61)
                if v62 == nil then
                    return;
                end;
                if v61 <= v57:count() and p_u_24._players._slots:contains(p_u_24:get_local_game_slot()) then
                    local v63 = v57:get(v61)
                    v62:set_player_info(v63, v61, v_u_10:accuracy_to_rank_value(v63._accuracy), v57:get(v61)._id == p_u_24._players._slots:get(p_u_24:get_local_game_slot())._id)
                    if p56 == true then
                        v62:show_in((v61 - 1) * 15)
                    end;
                else
                    v62:set_visible(false)
                end;
            end;
        end;
        v_u_25.update_labels = function(_) --[[ Name: update_labels ]] --[[ Line: 280 ]]
            --[[ Upvalues: (ref 1): v_u_27, (copy 2): p_u_24, (copy 3): p_u_23, (ref 4): v_u_8, (ref 5): v_u_17, (ref 6): v_u_10, (ref 7): v_u_7 ]]
            local v74, v75 = pcall(function() --[[ Line: 281 ]]
                --[[ Upvalues: (ref 1): v_u_27, (ref 2): p_u_24, (ref 3): p_u_23, (ref 4): v_u_8, (ref 5): v_u_17, (ref 6): v_u_10 ]]
                local l_PerformanceDisplaySection_0 = v_u_27.MainSurface.SurfaceGui.Frame.PerformanceDisplaySection
                local v64 = p_u_24:es_gamelocal_get_audiomanager():get_song_key()
                l_PerformanceDisplaySection_0.SongPanel.FavoriteDisplay.Visible = p_u_23._player_blob_manager:is_songkey_favorite(v64)
                v_u_8:singleton():render_coverimage_for_key(l_PerformanceDisplaySection_0.SongPanel.AlbumArt, l_PerformanceDisplaySection_0.SongPanel.AlbumArtOverlay, v64)
                v_u_17:render_songkey_colorsection(v64, l_PerformanceDisplaySection_0.SongPanel.ColorSection)
                local v65 = p_u_24._players._slots:get(p_u_24:get_local_game_slot())
                local v66, v67, v68, v69, v70, v71, v72, v73
                if v65 == nil then
                    v66 = 0
                    v67 = false
                    v68 = 0
                    v69 = 0
                    v70 = 0
                    v71 = 0
                    v72 = 0
                    v73 = 0
                else
                    v69 = v65._accuracy
                    v70 = v65._perfect_count
                    v71 = v65._great_count
                    v72 = v65._okay_count
                    v73 = v65._miss_count
                    v66 = v65._combo_max
                    v68 = v65._fever_percentage
                    v67 = v65._has_game_end_info
                end;
                if v67 then
                    l_PerformanceDisplaySection_0.RankIcon.Display.Icon.Image = v_u_10:get_rank_value_icon((v_u_10:accuracy_to_rank_value(v69)))
                    l_PerformanceDisplaySection_0.RankIcon.Display.Icon.Visible = true
                    l_PerformanceDisplaySection_0.PerfectDisplay.Text = string.format("%d", v70)
                    l_PerformanceDisplaySection_0.GreatDisplay.Text = string.format("%d", v71)
                    l_PerformanceDisplaySection_0.OkayDisplay.Text = string.format("%d", v72)
                    l_PerformanceDisplaySection_0.MissDisplay.Text = string.format("%d", v73)
                    l_PerformanceDisplaySection_0.AccuracyDisplay.Text = string.format("%.2f%%", v69 * 100)
                    l_PerformanceDisplaySection_0.MaxComboDisplay.Text = string.format("%d", v66)
                    l_PerformanceDisplaySection_0.FeverPercentDisplay.Text = string.format("%d%%", (math.floor(v68 * 100)))
                else
                    l_PerformanceDisplaySection_0.RankIcon.Display.Icon.Visible = false
                    l_PerformanceDisplaySection_0.PerfectDisplay.Text = "-"
                    l_PerformanceDisplaySection_0.GreatDisplay.Text = "-"
                    l_PerformanceDisplaySection_0.OkayDisplay.Text = "-"
                    l_PerformanceDisplaySection_0.MissDisplay.Text = "-"
                    l_PerformanceDisplaySection_0.AccuracyDisplay.Text = "Loading..."
                    l_PerformanceDisplaySection_0.MaxComboDisplay.Text = "-"
                    l_PerformanceDisplaySection_0.FeverPercentDisplay.Text = "-"
                end;
            end)
            if v74 ~= true then
                v_u_7:warnf("GameEndV2UI:update_labels err(%s)", v75)
            end;
        end;
        v_u_25.on_close_button = function(p76) --[[ Name: on_close_button ]] --[[ Line: 344 ]]
            --[[ Upvalues: (copy 1): l__menus_0 ]]
            l__menus_0:remove_menu(p76)
        end;
        local v_u_77 = nil
        v_u_25.on_play_again_pressed = function(p78) --[[ Name: on_play_again_pressed ]] --[[ Line: 349 ]]
            --[[ Upvalues: (copy 1): p_u_24, (ref 2): v_u_77, (ref 3): v_u_21 ]]
            local v_u_79 = p_u_24:get_event_info()
            local v_u_80 = p_u_24:es_gamelocal_get_audiomanager():get_song_key()
            v_u_77 = function(p81) --[[ Line: 352 ]]
                --[[ Upvalues: (copy 1): v_u_79, (ref 2): v_u_21, (copy 3): v_u_80 ]]
                p81._lobby_join:push_ui_to_lobby(function(p82) --[[ Line: 353 ]]
                    --[[ Upvalues: (ref 1): v_u_79, (ref 2): v_u_21, (ref 3): v_u_80 ]]
                    p82._game_join_protocol:set_event_info(v_u_79)
                    p82._menus:push_menu(v_u_21:new(p82, p82._spui, p82._menus, v_u_80, nil))
                end)
            end
            p78:on_close_button()
        end;
        local v_u_83 = false
        v_u_25.behaviour_update = function(p84, p85, _) --[[ Name: behaviour_update ]] --[[ Line: 365 ]]
            --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_29, (ref 3): v_u_31, (ref 4): v_u_32, (ref 5): v_u_30, (ref 6): v_u_6, (ref 7): v_u_13, (ref 8): v_u_33, (ref 9): v_u_83, (ref 10): v_u_34, (ref 11): v_u_35, (ref 12): v_u_36, (ref 13): v_u_39, (ref 14): v_u_42, (ref 15): v_u_40, (copy 16): p_u_24, (ref 17): v_u_1, (ref 18): v_u_7 ]]
            p84:behaviour_update_base(p85, p_u_23)
            v_u_29:behaviour_update(p85)
            v_u_31:behaviour_update(p85)
            v_u_32:behaviour_update(p85)
            local v86 = v_u_30
            v_u_30 = v_u_30 + v_u_6:TimescaleToDeltaTime(p85)
            if v86 < 3.5 and v_u_30 > 3.5 then
                p_u_23._bgm_manager:play_bgm(v_u_13.BGM_SONGEND)
            end;
            local v87 = v_u_33:get_selected()
            if v87 ~= v_u_83 then
                if v87 then
                    v_u_34.Visible = false
                    v_u_35.Visible = true
                    if v_u_36:has_rendered_graph() == false then
                        v_u_36:render_graph()
                    end;
                    v_u_39:set_visible(false)
                    v_u_42:set_visible(false)
                else
                    v_u_34.Visible = true
                    v_u_35.Visible = false
                    v_u_39:set_visible(true)
                    v_u_42:set_visible(true)
                end;
            end;
            v_u_83 = v87
            if v_u_40 ~= p_u_24._players:get_last_updated_time() then
                v_u_40 = p_u_24._players:get_last_updated_time()
                if v_u_1:is_dev_build() then
                    v_u_7:puts("GameEndV2UI:update_labels _ui_updated_time(%.2f)", v_u_40)
                end;
                p84:update_labels()
                p84:set_display_mode(false)
            end;
        end;
        v_u_25.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 408 ]]
            --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_26, (copy 3): p_u_23, (ref 4): v_u_27, (ref 5): v_u_31, (ref 6): v_u_32, (copy 7): p_u_24, (ref 8): v_u_77 ]]
            v_u_29:cleanup()
            for v88 = 1, v_u_26:count() do
                v_u_26:get(v88):do_remove(p_u_23)
            end;
            v_u_26:clear()
            v_u_26 = nil
            v_u_27:Destroy()
            v_u_31 = nil
            v_u_32 = nil
            if p_u_24:is_spectate() then
                p_u_24:get_spectate_manager():spectate_leave()
            else
                p_u_24:exit_to_lobby(v_u_77)
            end;
        end;
        v_u_25.layout = function(p89) --[[ Name: layout ]] --[[ Line: 430 ]]
            --[[ Upvalues: (copy 1): l__spui_0, (ref 2): v_u_28, (ref 3): v_u_27, (ref 4): v_u_31, (ref 5): v_u_32 ]]
            l__spui_0:uiobj_rescale_to_max_nxy(p89, 0.88, 0.88, v_u_28)
            v_u_27:SetPrimaryPartCFrame(l__spui_0:get_cframe({
                ["PositionNXY"] = Vector2.new(0.525, 0.5),
                ["OffsetXYZ"] = p89:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            }))
            v_u_31:layout()
            v_u_32:layout()
        end;
        v_u_25.visual_update = function(p90, p91, _) --[[ Name: visual_update ]] --[[ Line: 442 ]]
            --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_26 ]]
            p90:visual_update_base(p91, p_u_23)
            for v92 = 1, v_u_26:count() do
                v_u_26:get(v92):visual_update(p91, p_u_23)
            end;
        end;
        local v_u_93 = -1
        v_u_25.set_alpha = function(_, p94, p95) --[[ Name: set_alpha ]] --[[ Line: 452 ]]
            --[[ Upvalues: (ref 1): v_u_93, (ref 2): v_u_1, (ref 3): v_u_27 ]]
            if v_u_93 ~= p94 or p95 == true then
                v_u_93 = p94
                v_u_1:r_set_alpha(v_u_27, v_u_93)
            end;
        end;
        v_u_25.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 458 ]]
            --[[ Upvalues: (ref 1): v_u_93 ]]
            return v_u_93;
        end;
        v_u_25.set_scale = function(_, p96) --[[ Name: set_scale ]] --[[ Line: 459 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            v_u_28 = p96
        end;
        v_u_25.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 460 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28;
        end;
        v_u_25.get_native_size = function(p97) --[[ Name: get_native_size ]] --[[ Line: 462 ]]
            return p97._native_size;
        end;
        v_u_25.get_size = function(p98) --[[ Name: get_size ]] --[[ Line: 465 ]]
            return p98._size;
        end;
        v_u_25.set_size = function(p99, p100) --[[ Name: set_size ]] --[[ Line: 468 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            p99._size = p100
            v_u_27.PrimaryPart.Size = Vector3.new(p100.X, p100.Y, 0)
        end;
        v_u_25.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 472 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            return v_u_27.PrimaryPart.Position;
        end;
        v_u_25.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 475 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            return v_u_27.PrimaryPart.SurfaceGui;
        end;
        v_u_25.set_showing = function(_, p101) --[[ Name: set_showing ]] --[[ Line: 478 ]]
            --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_15 ]]
            if p101 then
                v_u_27.Parent = v_u_15:get_world_ui_folder()
            else
                v_u_27.Parent = nil
            end;
        end;
        f_cons()
        return v_u_25;
    end
};
