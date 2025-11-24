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
require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_11 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_12 = require(game.ReplicatedStorage.Lobby.UI.TabControllerBase)
local v_u_13 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_14 = require(game.ReplicatedStorage.Shared.EventLeaderboardInfo)
local v15 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_16 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_17 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_18 = require(game.ReplicatedStorage.PlayerInfo.EventLeaderboardRewards)
require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
local v_u_19 = require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_20 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_21 = nil
v15:require_client(function() --[[ Line: 30 ]]
    --[[ Upvalues: (ref 1): v_u_21 ]]
    v_u_21 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
end)
local v_u_22 = {
    ["Mode"] = {
        ["Loading"] = 1,
        ["Loaded"] = 2
    }
}
local v_u_23 = false
local v_u_24 = 0
local v_u_41 = {
    ["new"] = function(_, _, _, p_u_25, p_u_26) --[[ Name: new ]] --[[ Line: 45 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_1, (copy 3): v_u_18, (copy 4): v_u_19 ]]
        local v27 = {}
        local v_u_28 = nil
        local v_u_29 = nil
        local l_PlayerProto_0 = p_u_26.PrimaryPart.SurfaceGui.PlayerProto
        local v_u_30 = nil
        local v_u_31 = nil
        local v_u_32 = nil
        local v_u_33 = nil
        local v_u_34 = nil
        local v_u_35 = nil
        local v_u_36 = nil
        local v_u_37 = nil
        v27.cons = function(_) --[[ Name: cons ]] --[[ Line: 61 ]]
            --[[ Upvalues: (ref 1): v_u_28, (ref 2): v_u_4, (copy 3): p_u_25, (copy 4): p_u_26, (ref 5): v_u_30, (copy 6): l_PlayerProto_0, (ref 7): v_u_31, (ref 8): v_u_32, (ref 9): v_u_33, (ref 10): v_u_34, (ref 11): v_u_35, (ref 12): v_u_36, (ref 13): v_u_37 ]]
            v_u_28 = v_u_4:new(p_u_25, p_u_25:get_uichild_parent(), p_u_26.PrimaryPart):set_default_sgui()
            v_u_30 = l_PlayerProto_0
            v_u_31 = v_u_30.NameDisplay
            v_u_32 = v_u_30.Bubble.PlaceDisplay
            v_u_33 = v_u_30.GearMultiplierDisplay
            v_u_34 = v_u_30.ScoreDisplay
            v_u_35 = v_u_30.PlayerIconDisplay
            v_u_36 = v_u_30.Bubble
            v_u_37 = v_u_30.AudioModDisplay
        end;
        v27.set_display_element = function(_, p38) --[[ Name: set_display_element ]] --[[ Line: 73 ]]
            --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_28, (ref 3): v_u_31, (ref 4): v_u_32, (ref 5): v_u_1, (ref 6): v_u_33, (ref 7): v_u_34, (ref 8): v_u_35, (ref 9): v_u_36, (ref 10): v_u_18, (ref 11): v_u_37, (ref 12): v_u_19 ]]
            v_u_29 = p38
            if v_u_29 then
                v_u_28:set_visible(true)
                v_u_31.Text = v_u_29:get_name()
                v_u_32.Text = v_u_1:num_placify(v_u_29:get_place())
                v_u_33.Text = string.format("%.2f", v_u_29:get_best_score_gear_multiplier())
                v_u_34.Text = v_u_1:comma_value(v_u_29:get_best_score())
                v_u_35.Image = v_u_1:transparent_assetid()
                v_u_1:get_user_thumbnail(v_u_29:get_rbxid(), function(p39) --[[ Line: 82 ]]
                    --[[ Upvalues: (ref 1): v_u_35 ]]
                    v_u_35.Image = p39
                end, false)
                v_u_36.Image = v_u_18:place_to_bubble_icon(v_u_29:get_place())
                v_u_37.Image = v_u_19:mod_get_image(v_u_29:get_audiomod())
            else
                v_u_28:set_visible(false)
            end;
        end;
        v27.get_data = function(_) --[[ Name: get_data ]] --[[ Line: 90 ]]
            --[[ Upvalues: (ref 1): v_u_29 ]]
            return v_u_29;
        end;
        v27.set_visible = function(_, p40) --[[ Name: set_visible ]] --[[ Line: 92 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            v_u_28:set_visible(p40)
        end;
        v27.layout = function(_) --[[ Name: layout ]] --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            v_u_28:layout()
        end;
        v27:cons()
        return v27;
    end
}
v_u_22.new = function(_, p_u_42, p_u_43, p_u_44, p_u_45) --[[ Name: new ]] --[[ Line: 104 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): v_u_2, (copy 3): v_u_19, (copy 4): v_u_20, (copy 5): v_u_10, (copy 6): v_u_22, (copy 7): v_u_5, (copy 8): v_u_4, (copy 9): v_u_7, (copy 10): v_u_6, (ref 11): v_u_21, (copy 12): v_u_9, (copy 13): v_u_13, (copy 14): v_u_3, (copy 15): v_u_41, (copy 16): v_u_11, (copy 17): v_u_14, (copy 18): v_u_1, (copy 19): v_u_18, (copy 20): v_u_16, (copy 21): v_u_17, (copy 22): v_u_8, (ref 23): v_u_23 ]]
    local v_u_46 = v_u_12:new()
    local v_u_47 = nil
    local v_u_48 = nil
    local v_u_49 = 0
    local v_u_50 = nil
    local v_u_51 = nil
    local v_u_52 = nil
    local v_u_53 = nil
    local v_u_54 = nil
    local v_u_55 = nil
    local v_u_56 = nil
    local v_u_57 = nil
    local v_u_58 = nil
    local v_u_59 = nil
    local v_u_60 = nil
    local v_u_61 = nil
    local v_u_62 = nil
    local v_u_63 = nil
    local v_u_64 = v_u_2:new()
    local l_Normal_0 = v_u_19.Normal
    local function _() --[[ Name: hide_info_audiomod_to_buttons ]] --[[ Line: 122 ]]
        --[[ Upvalues: (copy 1): v_u_64 ]]
        for _, v65 in v_u_64:key_itr() do
            v65:set_visible(false)
        end;
    end;
    local function _(p66) --[[ Name: select_audiomod ]] --[[ Line: 128 ]]
        --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_19, (ref 3): l_Normal_0, (copy 4): v_u_46 ]]
        v_u_20:is_enum_member(p66, v_u_19)
        l_Normal_0 = p66
        v_u_46:refresh()
    end;
    local function _(p67, p68) --[[ Name: get_mode_for_songkey ]] --[[ Line: 134 ]]
        --[[ Upvalues: (ref 1): v_u_10 ]]
        local v69 = v_u_10:singleton():get_audiomod_to_modes_of_songkey(p67)
        if v69:contains(p68) then
            return v69:get(p68);
        else
            return p67;
        end;
    end;
    local l_Loading_0 = v_u_22.Mode.Loading
    v_u_46.cons = function(p_u_70) --[[ Name: cons ]] --[[ Line: 145 ]]
        --[[ Upvalues: (ref 1): v_u_47, (copy 2): p_u_44, (ref 3): v_u_57, (ref 4): v_u_58, (ref 5): v_u_59, (ref 6): v_u_60, (ref 7): v_u_56, (ref 8): v_u_55, (ref 9): v_u_54, (ref 10): v_u_52, (ref 11): v_u_53, (ref 12): v_u_62, (copy 13): p_u_43, (copy 14): p_u_42, (ref 15): v_u_5, (ref 16): v_u_4, (ref 17): v_u_61, (ref 18): v_u_7, (ref 19): v_u_10, (ref 20): v_u_6, (ref 21): l_Normal_0, (ref 22): v_u_21, (ref 23): v_u_50, (ref 24): v_u_48, (ref 25): v_u_51, (ref 26): v_u_63, (copy 27): p_u_45, (ref 28): v_u_9, (ref 29): v_u_13, (ref 30): v_u_3, (ref 31): v_u_49, (ref 32): v_u_41, (ref 33): v_u_20, (ref 34): v_u_19, (copy 35): v_u_46, (copy 36): v_u_64 ]]
        v_u_47 = p_u_44.MainSurface.SurfaceGui.Frame.TabLeaderboard
        v_u_47.Visible = false
        v_u_57 = v_u_47.LoadingFrame
        v_u_58 = v_u_47.LoadedFrame
        v_u_59 = v_u_47.NoLeaderboardFrame
        v_u_60 = v_u_58.NoEntriesFrame
        v_u_56 = v_u_58.YouDisplay
        v_u_55 = v_u_58.TimeRemainingSection.TimeRemainingText
        v_u_54 = v_u_58.TimeRemainingSection.TimeRemainingDisplay
        v_u_52 = v_u_58.PageDisplaySection.CurrentPageDisplay
        v_u_53 = v_u_58.PageDisplaySection.MaxPageDisplay
        v_u_62 = p_u_43:add_cycle_element(p_u_42, 1, v_u_5:new(v_u_4:new(p_u_43, p_u_44.PrimaryPart, p_u_44.TabLeaderboardElements.PlayButton), p_u_42._spui, function() --[[ Line: 163 ]]
            --[[ Upvalues: (ref 1): v_u_61, (ref 2): p_u_42, (ref 3): v_u_7, (ref 4): v_u_10, (ref 5): v_u_6, (ref 6): l_Normal_0, (ref 7): v_u_21 ]]
            if v_u_61 ~= nil then
                p_u_42._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
                local v71 = v_u_61:get_song_key()
                if v71 == v_u_10:invalid_songkey() then
                    return v_u_6:warnf("NewSongEventUI:play_button_pressed invalid songkey");
                end;
                local v72 = l_Normal_0
                local v73 = v_u_10:singleton():get_audiomod_to_modes_of_songkey(v71)
                if v73:contains(v72) then
                    v71 = v73:get(v72)
                end;
                local v74 = p_u_42._lobby_join:get_lobby()
                v74:songkey_opt_set_artist_event_info(v71)
                p_u_42._menus:push_menu(v_u_21:new(v74, p_u_42._spui, p_u_42._menus, v71, nil))
            end;
        end))
        v_u_50 = p_u_43:add_cycle_element(p_u_42, 1, v_u_5:new(v_u_4:new(p_u_43, p_u_44.PrimaryPart, p_u_44.TabLeaderboardElements.ArrowLeft), p_u_42._spui, function() --[[ Line: 181 ]]
            --[[ Upvalues: (ref 1): p_u_42, (ref 2): v_u_7, (ref 3): v_u_48 ]]
            p_u_42._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_48:prev_page()
        end))
        v_u_51 = p_u_43:add_cycle_element(p_u_42, 1, v_u_5:new(v_u_4:new(p_u_43, p_u_44.PrimaryPart, p_u_44.TabLeaderboardElements.ArrowRight), p_u_42._spui, function() --[[ Line: 190 ]]
            --[[ Upvalues: (ref 1): p_u_42, (ref 2): v_u_7, (ref 3): v_u_48 ]]
            p_u_42._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_48:next_page()
        end))
        v_u_63 = p_u_43:add_cycle_element(p_u_42, 1, v_u_5:new(v_u_4:new(p_u_43, p_u_44.PrimaryPart, p_u_44.TabLeaderboardElements.InfoButton), p_u_42._spui, function() --[[ Line: 199 ]]
            --[[ Upvalues: (ref 1): p_u_42, (ref 2): v_u_7, (ref 3): p_u_45, (ref 4): v_u_9 ]]
            p_u_42._sfx_manager:play_sfx(v_u_7.SFX_MENU_CLOSE)
            p_u_45:push_menu(v_u_9:new(p_u_42, p_u_42._spui, p_u_45):set_text("Event Leaderboards", "Compete in a server-wide limited time leaderboard to earn event points! Leaderboards start every 5 to 10 minutes, and last 15 minutes each. Play any available mode of the selected song during the event leaderboard period to enter. Your entry is valid while you remain connected to the server, and rewards can be claimed after the event completes. Event point rewards are scaled based on the number of entries, and rank among entries:\n1st place with 25 entries - 750 event points\n1st place with 1 entry - 100 event points"))
        end))
        v_u_48 = v_u_13:new():set_fn_get_data_list(function() --[[ Line: 215 ]]
            --[[ Upvalues: (ref 1): v_u_61, (ref 2): v_u_3 ]]
            if v_u_61 == nil then
                return v_u_3:new();
            else
                return v_u_61:get_member_places();
            end;
        end):set_fn_set_element_data(function(p75, p76) --[[ Line: 219 ]]
            if p76 == nil then
                p75:set_visible(false)
            else
                p75:set_visible(true)
                p75:set_display_element(p76)
            end;
        end):set_fn_next_prev_visible(function(p77, p78) --[[ Line: 227 ]]
            --[[ Upvalues: (ref 1): v_u_51, (ref 2): v_u_50 ]]
            v_u_51:set_visible(p77)
            v_u_50:set_visible(p78)
        end):set_fn_update_page_display(function(p79, p80) --[[ Line: 231 ]]
            --[[ Upvalues: (ref 1): v_u_52, (ref 2): v_u_53 ]]
            v_u_52.Text = tostring(p79)
            v_u_53.Text = tostring(p80)
        end):set_do_wrap(true):set_i_offset(v_u_49):set_fn_store_i_offset(function(p81) --[[ Line: 237 ]]
            --[[ Upvalues: (ref 1): v_u_49 ]]
            v_u_49 = p81
        end):set_fn_is_empty(function(p82) --[[ Line: 240 ]]
            --[[ Upvalues: (ref 1): v_u_60 ]]
            v_u_60.Visible = p82
        end)
        local l_Anchors_0 = p_u_44.TabLeaderboardElements.Anchors
        v_u_48:create_list_elements_from_anchors_and_proto({
            l_Anchors_0.Anchor1,
            l_Anchors_0.Anchor2,
            l_Anchors_0.Anchor3,
            l_Anchors_0.Anchor4,
            l_Anchors_0.Anchor5
        }, p_u_44.TabLeaderboardElements.LeaderboardElementProto, p_u_44, function(p83) --[[ Line: 255 ]]
            --[[ Upvalues: (ref 1): v_u_41, (ref 2): p_u_42, (copy 3): p_u_70, (ref 4): p_u_43 ]]
            return v_u_41:new(p_u_42, p_u_70, p_u_43, p83);
        end)
        local function f_create_info_to_audiomod_button(p_u_84, p85) --[[ Name: create_info_to_audiomod_button ]] --[[ Line: 260 ]]
            --[[ Upvalues: (ref 1): p_u_43, (ref 2): p_u_42, (ref 3): v_u_5, (ref 4): v_u_4, (ref 5): p_u_44, (ref 6): v_u_7, (ref 7): v_u_20, (ref 8): v_u_19, (ref 9): l_Normal_0, (ref 10): v_u_46, (ref 11): v_u_10, (ref 12): v_u_64 ]]
            local v87 = p_u_43:add_cycle_element(p_u_42, 1, v_u_5:new(v_u_4:new(p_u_43, p_u_44.PrimaryPart, p85), p_u_42._spui, function() --[[ Line: 265 ]]
                --[[ Upvalues: (ref 1): p_u_42, (ref 2): v_u_7, (copy 3): p_u_84, (ref 4): v_u_20, (ref 5): v_u_19, (ref 6): l_Normal_0, (ref 7): v_u_46 ]]
                p_u_42._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                local v86 = p_u_84
                v_u_20:is_enum_member(v86, v_u_19)
                l_Normal_0 = v86
                v_u_46:refresh()
            end):set_auto_zoffset_behaviour(true))
            v87:bind_data({
                ["Toggle"] = v_u_5:button_bind_anim_toggle(v87, function() --[[ Line: 271 ]]
                    --[[ Upvalues: (ref 1): p_u_43 ]]
                    return p_u_43:get_alpha();
                end),
                ["DifficultyDisplay"] = p85.SurfaceGui.Button.DifficultyDisplay,
                ["TargetSongKey"] = v_u_10:invalid_songkey()
            })
            v87:set_visible(false)
            v_u_64:add(p_u_84, v87)
        end;
        f_create_info_to_audiomod_button(v_u_19.Easy, p_u_44.TabLeaderboardElements.SongInfoButtons.EasyModeButton)
        f_create_info_to_audiomod_button(v_u_19.Normal, p_u_44.TabLeaderboardElements.SongInfoButtons.NormalModeButton)
        f_create_info_to_audiomod_button(v_u_19.Hard, p_u_44.TabLeaderboardElements.SongInfoButtons.HardModeButton)
        for _, v88 in v_u_64:key_itr() do
            v88:set_visible(false)
        end;
        p_u_70:refresh()
    end;
    v_u_46.render_leaderboard_song_info = function(p89) --[[ Name: render_leaderboard_song_info ]] --[[ Line: 286 ]]
        --[[ Upvalues: (ref 1): v_u_61, (ref 2): v_u_6, (ref 3): v_u_58, (ref 4): v_u_10, (ref 5): v_u_11, (ref 6): v_u_14, (ref 7): v_u_62, (copy 8): p_u_43, (copy 9): v_u_64, (ref 10): v_u_19, (ref 11): l_Normal_0, (ref 12): v_u_56, (ref 13): v_u_1, (ref 14): v_u_18 ]]
        if v_u_61 == nil then
            return v_u_6:warnf("_leaderboard_info is nil");
        elseif v_u_58:FindFirstChild("SongTitleDisplay") ~= nil then
            local v90 = v_u_61:get_song_key()
            v_u_58.SongTitleDisplay.Text = v_u_10:singleton():get_title_for_key(v90)
            v_u_10:singleton():render_coverimage_for_key(v_u_58.SongDisplaySection.Icon, v_u_58.SongDisplaySection.IconOverlay, v90)
            v_u_11:render_songkey_colorsection(v90, v_u_58.SongDisplaySection.ColorSection)
            p89:render_time_remaining()
            if v_u_61:get_state() == v_u_14.State.Active then
                v_u_62:set_visible(true)
                p_u_43:preview_songkey(v90)
                local v91 = v_u_10:singleton():key_get_audiomod(v90)
                local v92 = v_u_10:singleton():get_audiomod_to_modes_of_songkey(v90)
                for v93, v94 in v_u_64:key_itr() do
                    v94:set_visible(true)
                    local l_Toggle_0 = v94:get_bound_data().Toggle
                    local l_DifficultyDisplay_0 = v94:get_bound_data().DifficultyDisplay
                    local v95 = false
                    if v92:contains(v93) then
                        local v96 = v92:get(v93)
                        v94:get_bound_data().TargetSongKey = v96
                        l_DifficultyDisplay_0.Text = tostring((v_u_10:singleton():get_difficulty_for_key(v96)))
                        l_DifficultyDisplay_0.TextColor3 = v_u_10:singleton():get_difficulty_color_for_key(v96)
                        v95 = v95 == false and v_u_19:mod_to_compare_value(v91) >= v_u_19:mod_to_compare_value(v93) and true or v95
                        if v95 then
                            v94:set_enabled(true)
                            if l_Normal_0 == v93 then
                                v94:set_scale(1.35)
                                v94:set_unselected_zoffset(750)
                                v94:set_passive_anim(true)
                                l_Toggle_0:set_toggle(true)
                            else
                                v94:set_scale(0.85)
                                v94:set_unselected_zoffset(500)
                                v94:set_passive_anim(false)
                                l_Toggle_0:set_toggle_off_alpha(0.75)
                                l_Toggle_0:set_toggle(false)
                            end;
                        end;
                    end;
                    if v95 == false then
                        v94:get_bound_data().TargetSongKey = v_u_10:invalid_songkey()
                        l_DifficultyDisplay_0.Text = "-"
                        l_DifficultyDisplay_0.TextColor3 = Color3.new(1, 1, 1)
                        v94:set_enabled(false)
                        l_Toggle_0:set_toggle_off_alpha(0.2)
                        l_Toggle_0:set_toggle(false)
                        v94:set_scale(0.85)
                        v94:set_unselected_zoffset(500)
                    end;
                end;
            else
                v_u_62:set_visible(false)
                for _, v97 in v_u_64:key_itr() do
                    v97:set_visible(false)
                end;
            end;
            v_u_58.YouNotEnteredDisplay.Visible = true
            v_u_56.Visible = false
            for _, v98 in v_u_61:get_member_places():key_itr() do
                if v98:get_rbxid() == v_u_1:get_local_userid() then
                    v_u_56.Visible = true
                    v_u_56.Bubble.PlaceDisplay.Text = v_u_1:num_placify(v98:get_place())
                    v_u_56.ScoreDisplay.Text = v_u_1:comma_value(v98:get_best_score())
                    v_u_56.PlayerIconDisplay.Image = v_u_1:transparent_assetid()
                    v_u_1:get_user_thumbnail(v98:get_rbxid(), function(p99) --[[ Line: 368 ]]
                        --[[ Upvalues: (ref 1): v_u_56 ]]
                        v_u_56.PlayerIconDisplay.Image = p99
                    end, false)
                    v_u_56.Bubble.Image = v_u_18:place_to_bubble_icon(v98:get_place())
                    v_u_56.AudioModDisplay.Image = v_u_19:mod_get_image(v98:get_audiomod())
                    v_u_58.YouNotEnteredDisplay.Visible = false
                    return;
                end;
            end;
        end;
    end;
    v_u_46.render_time_remaining = function(_) --[[ Name: render_time_remaining ]] --[[ Line: 379 ]]
        --[[ Upvalues: (ref 1): v_u_61, (ref 2): v_u_14, (ref 3): v_u_54, (ref 4): v_u_1, (ref 5): v_u_55 ]]
        if v_u_61 ~= nil then
            if v_u_61:get_state() == v_u_14.State.Active then
                v_u_54.Text = v_u_1:format_sec_time(v_u_61:get_time_remaining())
                v_u_54.TextColor3 = v_u_1:color3(255, 255, 255)
                v_u_55.Text = "Time Remaining..."
                return;
            end;
            if v_u_61:get_state() == v_u_14.State.Closing then
                v_u_54.Text = v_u_1:format_sec_time(v_u_61:get_closing_time_remaining())
                v_u_54.TextColor3 = v_u_1:color3(185, 185, 185)
                v_u_55.Text = "Closing in..."
                return;
            end;
            if v_u_61:get_state() == v_u_14.State.Ended then
                v_u_54.Text = "-"
                v_u_54.TextColor3 = v_u_1:color3(150, 150, 150)
                v_u_55.Text = "Leaderboard has closed."
            end;
        end;
    end;
    v_u_46.behaviour_update = function(p_u_100, p101) --[[ Name: behaviour_update ]] --[[ Line: 401 ]]
        --[[ Upvalues: (ref 1): v_u_61, (ref 2): v_u_1, (ref 3): v_u_16, (copy 4): p_u_42, (ref 5): v_u_17, (ref 6): v_u_6, (ref 7): v_u_8 ]]
        if v_u_61 ~= nil then
            local v102 = v_u_61:get_state()
            v_u_61:update(p101)
            p_u_100:render_time_remaining()
            if v102 ~= v_u_61:get_state() then
                p_u_100:load_data(function() --[[ Line: 407 ]]
                    --[[ Upvalues: (copy 1): p_u_100 ]]
                    p_u_100:refresh()
                end)
            end;
        end;
        if v_u_1:is_dev_build() and (v_u_16.DebugEventLeaderboardKey == true and p_u_42._input:control_just_pressed(v_u_17.KEY_DEBUG_3)) then
            v_u_6:warnf("DebugEventLeaderboardKey")
            p_u_42._evt:clear_pending_on(v_u_8.EVT_LeaderboardEvent_ServerDebugLeaderboardResponse)
            p_u_42._evt:wait_on_event_once(v_u_8.EVT_LeaderboardEvent_ServerDebugLeaderboardResponse, function() --[[ Line: 416 ]]
                --[[ Upvalues: (copy 1): p_u_100 ]]
                p_u_100:load_data(function() --[[ Line: 417 ]]
                    --[[ Upvalues: (ref 1): p_u_100 ]]
                    p_u_100:refresh()
                end)
            end)
            p_u_42._evt:fire_event_to_server(v_u_8.EVT_LeaderboardEvent_ClientDebugLeaderboard)
        end;
    end;
    local v_u_103 = nil
    v_u_46.set_visible = function(_, p104) --[[ Name: set_visible ]] --[[ Line: 426 ]]
        --[[ Upvalues: (ref 1): v_u_103, (ref 2): v_u_47, (ref 3): v_u_48, (ref 4): v_u_62, (ref 5): v_u_63, (copy 6): v_u_64 ]]
        v_u_103 = p104
        v_u_47.Visible = p104
        if v_u_103 ~= true then
            v_u_48:set_visible(false)
            v_u_62:set_visible(false)
            v_u_63:set_visible(false)
            for _, v105 in v_u_64:key_itr() do
                v105:set_visible(false)
            end;
        end;
    end;
    v_u_46.load_data = function(p106, p_u_107) --[[ Name: load_data ]] --[[ Line: 437 ]]
        --[[ Upvalues: (ref 1): v_u_23, (ref 2): l_Loading_0, (ref 3): v_u_22, (copy 4): p_u_43, (copy 5): p_u_42, (ref 6): v_u_8, (ref 7): v_u_6, (ref 8): v_u_61, (ref 9): v_u_14, (ref 10): l_Normal_0, (ref 11): v_u_10, (copy 12): p_u_45, (ref 13): v_u_9, (ref 14): v_u_7 ]]
        v_u_23 = false
        l_Loading_0 = v_u_22.Mode.Loading
        p106:refresh()
        local v_u_108 = p_u_43:get_last_load_start_time()
        p_u_42._evt:clear_pending_on(v_u_8.EVT_LeaderboardEvent_ServerRequestLeaderboardDataResponse)
        p_u_42._evt:wait_on_event_once(v_u_8.EVT_LeaderboardEvent_ServerRequestLeaderboardDataResponse, function(p109, p110, p_u_111) --[[ Line: 444 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): l_Loading_0, (ref 3): v_u_22, (copy 4): v_u_108, (ref 5): p_u_43, (ref 6): v_u_61, (ref 7): v_u_14, (ref 8): l_Normal_0, (ref 9): v_u_10, (ref 10): p_u_45, (ref 11): v_u_9, (ref 12): p_u_42, (ref 13): p_u_107, (ref 14): v_u_7 ]]
            if p109 == nil then
                return v_u_6:warnf("EVT_LeaderboardEvent_ServerRequestLeaderboardDataResponse response nil");
            end;
            l_Loading_0 = v_u_22.Mode.Loaded
            if v_u_108 ~= p_u_43:get_last_load_start_time() then
                return v_u_6:warnf("data load cancelled");
            end;
            if #p109 >= 1 then
                v_u_61 = v_u_14:from_table(p109[#p109])
                l_Normal_0 = v_u_10:singleton():key_get_audiomod(v_u_61:get_song_key())
                if p110 and p_u_111 ~= nil then
                    local v_u_112 = p_u_45:push_menu(v_u_9:new(p_u_42, p_u_42._spui, p_u_45):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                    local v_u_113 = p_u_107
                    p_u_107 = nil
                    p_u_42._player_blob_manager:do_sync(function(_) --[[ Line: 463 ]]
                        --[[ Upvalues: (copy 1): v_u_113, (ref 2): p_u_42, (copy 3): v_u_112, (ref 4): v_u_7, (ref 5): p_u_43, (ref 6): p_u_45, (ref 7): v_u_9, (copy 8): p_u_111 ]]
                        v_u_113()
                        p_u_42._menus:remove_menu(v_u_112)
                        p_u_42._sfx_manager:play_sfx(v_u_7.SFX_ACQUIRE)
                        p_u_43:update_player_info_section()
                        p_u_45:push_menu(v_u_9:new(p_u_42, p_u_42._spui, p_u_45):set_text("Rewards", p_u_111))
                    end)
                end;
            else
                v_u_61 = nil
            end;
            if p_u_107 then
                p_u_107()
            end;
        end)
        p_u_42._evt:fire_event_to_server(v_u_8.EVT_LeaderboardEvent_ClientRequestLeaderboardData)
    end;
    v_u_46.refresh = function(p114) --[[ Name: refresh ]] --[[ Line: 486 ]]
        --[[ Upvalues: (ref 1): l_Loading_0, (ref 2): v_u_22, (ref 3): v_u_57, (ref 4): v_u_58, (ref 5): v_u_59, (ref 6): v_u_48, (ref 7): v_u_62, (ref 8): v_u_63, (copy 9): v_u_64, (ref 10): v_u_61 ]]
        if l_Loading_0 == v_u_22.Mode.Loading then
            v_u_57.Visible = true
            v_u_58.Visible = false
            v_u_59.Visible = false
            v_u_48:set_visible(false)
            v_u_62:set_visible(false)
            v_u_63:set_visible(false)
            for _, v115 in v_u_64:key_itr() do
                v115:set_visible(false)
            end;
        elseif l_Loading_0 == v_u_22.Mode.Loaded then
            v_u_57.Visible = false
            if v_u_61 ~= nil then
                v_u_58.Visible = true
                v_u_59.Visible = false
                v_u_48:set_visible(true)
                v_u_48:page_update()
                v_u_63:set_visible(true)
                p114:render_leaderboard_song_info()
                return;
            end;
            v_u_58.Visible = false
            v_u_59.Visible = true
            v_u_48:set_visible(false)
            v_u_62:set_visible(false)
            v_u_63:set_visible(false)
            for _, v116 in v_u_64:key_itr() do
                v116:set_visible(false)
            end;
        end;
    end;
    v_u_46.layout = function(_) --[[ Name: layout ]] --[[ Line: 516 ]]
        --[[ Upvalues: (ref 1): v_u_48 ]]
        v_u_48:layout()
    end;
    v_u_46.requires_reload_on_menu_refocus = function(_) --[[ Name: requires_reload_on_menu_refocus ]] --[[ Line: 519 ]]
        return true;
    end;
    v_u_46:cons()
    return v_u_46;
end;
v_u_22.set_notification_display = function(_, p117, p118) --[[ Name: set_notification_display ]] --[[ Line: 525 ]]
    --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_24 ]]
    v_u_23 = p117
    v_u_24 = p118
end;
v_u_22.has_notification = function(_) --[[ Name: has_notification ]] --[[ Line: 530 ]]
    --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_24 ]]
    return v_u_23, v_u_24;
end;
return v_u_22;
