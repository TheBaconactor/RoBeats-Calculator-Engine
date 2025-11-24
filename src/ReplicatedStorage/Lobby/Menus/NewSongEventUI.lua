-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:45 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_9 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_10 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_11 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.SongLaunchEventInfo)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_14 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_15 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
local v16 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_17 = nil
v16:require_client(function() --[[ Line: 23 ]]
    --[[ Upvalues: (ref 1): v_u_17 ]]
    v_u_17 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
end)
return {
    ["new"] = function(_, p_u_18, p_u_19, p_u_20) --[[ Name: new ]] --[[ Line: 30 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_11, (copy 3): v_u_1, (copy 4): v_u_10, (copy 5): v_u_5, (copy 6): v_u_4, (copy 7): v_u_7, (copy 8): v_u_12, (copy 9): v_u_6, (copy 10): v_u_13, (copy 11): v_u_2, (copy 12): v_u_14, (copy 13): v_u_15, (ref 14): v_u_17, (copy 15): v_u_9, (copy 16): v_u_8 ]]
        local v_u_21 = v_u_3:new(p_u_19, p_u_20)
        local v_u_22 = nil
        local v_u_23 = 1
        local v_u_24 = v_u_11:invalid_songkey()
        local v_u_25 = nil
        local v_u_26 = nil
        local v_u_27 = nil
        v_u_21.cons = function(_) --[[ Name: cons ]] --[[ Line: 42 ]]
            --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_1, (ref 3): v_u_10, (copy 4): v_u_21, (copy 5): p_u_18, (ref 6): v_u_5, (ref 7): v_u_4, (copy 8): p_u_19, (ref 9): v_u_7, (copy 10): p_u_20, (ref 11): v_u_12, (ref 12): v_u_27, (ref 13): v_u_6, (ref 14): v_u_25, (ref 15): v_u_13, (ref 16): v_u_26 ]]
            v_u_22 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.NewSongEventUI:Clone()
            v_u_22.Name = v_u_1:gen_name(v_u_22.Name)
            v_u_22.Parent = v_u_10:get_world_ui_folder()
            v_u_21._native_size = v_u_22.PrimaryPart.Size
            v_u_21._size = v_u_21._native_size
            v_u_21:add_cycle_element(p_u_18, 1, v_u_5:new(v_u_4:new(v_u_21, v_u_22.PrimaryPart, v_u_22.BackButtonSurface), p_u_19, function() --[[ Line: 53 ]]
                --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_7, (ref 3): p_u_20, (ref 4): v_u_21 ]]
                p_u_18._sfx_manager:play_sfx(v_u_7.SFX_MENU_CLOSE)
                p_u_20:remove_menu(v_u_21)
            end))
            local v28, v29 = v_u_12:is_song_launch_event_active(p_u_18._player_blob_manager:get_day_event_list())
            v_u_27 = v29
            if v28 == true then
                local v30 = p_u_18._player_blob_manager:get_player_blob()
                local l_Frame_0 = v_u_22.MainSurface.SurfaceGui.Frame
                v_u_25 = l_Frame_0.InfoSection
                v_u_25.LoadedSection.Visible = false
                v_u_25.EmptySection.Visible = true
                l_Frame_0.NewsArea.NewsSection.NewsHead.Text = v_u_12:get_news_title_for_event_id(v29)
                l_Frame_0.NewsArea.NewsSection.NewsSub.Text = v_u_12:get_news_sub_for_event_id(v29)
                l_Frame_0.NewsArea.NewsSection.NewsImage.Image = v_u_12:get_news_image_for_event_id(v29)
                local v31 = 0
                for v32, _ in v_u_12:get_song_set_for_event_id(v29):key_itr() do
                    if v_u_12:songkey_include_reward(v32) then
                        v31 = v31 + 1
                    end;
                end;
                local v33 = v_u_12:playerblob_eventid_reward_available(v30, v29)
                local l_RewardSection_0 = l_Frame_0.RewardSection
                local v34 = v31 - v_u_12:playerblob_get_remaining_songs_count_for_event_id(v30, v29)
                if v33 then
                    l_RewardSection_0.RewardDisplay.Text = string.format("Collected %d/%d Songs", v34, v31)
                else
                    l_RewardSection_0.RewardDisplay.Text = "Reward Claimed"
                end;
                v_u_13:currency_type_render_icon(v_u_12:get_event_reward_currency_type_for_event_id(v29), v_u_22.CollectRewardButton.SurfaceGui.Frame.RewardIcon)
                v_u_22.CollectRewardButton.SurfaceGui.Frame.AmountDisplay.Text = tostring(v_u_12:get_event_reward_currency_amount_for_event_id(v29))
                if v29 < v30.SongLaunchClaimedID and v33 == false then
                    l_RewardSection_0.Visible = false
                    v_u_22.CollectRewardButton.Parent = nil
                else
                    l_RewardSection_0.Visible = true
                    local v35 = v_u_21:add_cycle_element(p_u_18, 1, v_u_5:new(v_u_4:new(v_u_21, v_u_22.PrimaryPart, v_u_22.CollectRewardButton), p_u_19, function() --[[ Line: 107 ]]
                        --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_7, (ref 3): p_u_20, (ref 4): v_u_21 ]]
                        p_u_18._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
                        p_u_20:remove_menu(v_u_21)
                        v_u_21:claim_reward_button_pressed()
                    end))
                    v_u_5:button_add_enabled_anim(v35, function() --[[ Line: 113 ]]
                        --[[ Upvalues: (ref 1): v_u_21 ]]
                        return v_u_21:get_alpha();
                    end)
                    local v36 = v_u_12:playerblob_eventid_reward_available(v30, v29)
                    if v36 then
                        v36 = v_u_12:playerblob_get_remaining_songs_count_for_event_id(v30, v29) == 0
                    end;
                    v35:set_enabled(v36)
                end;
                v_u_26 = v_u_21:add_cycle_element(p_u_18, 1, v_u_5:new(v_u_4:new(v_u_21, v_u_22.PrimaryPart, v_u_22.PlayButtonSurface), p_u_18._spui, function() --[[ Line: 120 ]]
                    --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_7, (ref 3): v_u_21 ]]
                    p_u_18._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
                    v_u_21:play_button_pressed()
                end)):set_auto_zoffset_behaviour(true):set_passive_anim(true)
                v_u_26:set_visible(false)
                v_u_21:init_elements(v29)
            else
                v_u_6:warnf("NewSongEventUI attempted to open, SongLaunchEventInfo:is_song_launch_event_active false")
                p_u_20:remove_menu(v_u_21)
            end;
        end;
        v_u_21.init_elements = function(_, p37) --[[ Name: init_elements ]] --[[ Line: 130 ]]
            --[[ Upvalues: (copy 1): p_u_18, (ref 2): v_u_22, (ref 3): v_u_2, (ref 4): v_u_12, (ref 5): v_u_11, (copy 6): v_u_21, (ref 7): v_u_5, (ref 8): v_u_4, (ref 9): v_u_7, (ref 10): v_u_13 ]]
            local v_u_38 = p_u_18._player_blob_manager:get_player_blob()
            local l_SongElementProto_0 = v_u_22.SongElementProto
            l_SongElementProto_0.Parent = nil
            local v39 = v_u_2:new():push_back_table_list({
                v_u_22.Anchors.Anchor1,
                v_u_22.Anchors.Anchor2,
                v_u_22.Anchors.Anchor3,
                v_u_22.Anchors.Anchor4,
                v_u_22.Anchors.Anchor5,
                v_u_22.Anchors.Anchor6,
                v_u_22.Anchors.Anchor7,
                v_u_22.Anchors.Anchor8,
                v_u_22.Anchors.Anchor9,
                v_u_22.Anchors.Anchor10
            })
            local v40 = v_u_2:new()
            for v41, _ in v_u_12:get_song_set_for_event_id(p37):key_itr() do
                v40:push_back(v41)
            end;
            v40:sort(function(p42, p43) --[[ Line: 151 ]]
                --[[ Upvalues: (ref 1): v_u_11 ]]
                return v_u_11:singleton():get_difficulty_for_key(p43) - v_u_11:singleton():get_difficulty_for_key(p42);
            end)
            local v_u_44 = v_u_2:new()
            for v45 = 1, v39:count() do
                local v46 = v39:get(v45)
                v46.Parent = nil
                if v45 <= v40:count() then
                    local v_u_47 = v40:get(v45)
                    local v_u_48 = l_SongElementProto_0:Clone()
                    v_u_48:SetPrimaryPartCFrame(v46.PrimaryPart.CFrame)
                    v_u_48.Parent = v_u_22
                    local v_u_49 = nil
                    v_u_21:add_cycle_element(p_u_18, 1, v_u_5:new(v_u_4:new(v_u_21, v_u_22.PrimaryPart, v_u_48.PrimaryPart), p_u_18._spui, function() --[[ Line: 169 ]]
                        --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_7, (copy 3): v_u_44, (ref 4): v_u_49, (ref 5): v_u_21, (copy 6): v_u_47 ]]
                        p_u_18._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                        for v50 = 1, v_u_44:count() do
                            v_u_44:get(v50):set_selected(false)
                        end;
                        v_u_49:set_selected(true)
                        v_u_21:preview_songkey(v_u_47)
                    end)):set_auto_zoffset_behaviour(true)
                    v_u_49 = (function() --[[ Line: 178 ]]
                        --[[ Upvalues: (copy 1): v_u_48, (ref 2): v_u_11, (copy 3): v_u_47, (ref 4): v_u_12, (ref 5): v_u_13, (copy 6): v_u_38 ]]
                        local v51 = {}
                        local v_u_52 = nil
                        v51.cons = function(_) --[[ Name: cons ]] --[[ Line: 182 ]]
                            --[[ Upvalues: (ref 1): v_u_48, (ref 2): v_u_11, (ref 3): v_u_47, (ref 4): v_u_12, (ref 5): v_u_13, (ref 6): v_u_38, (ref 7): v_u_52 ]]
                            local l_Frame_1 = v_u_48.PrimaryPart.SurfaceGui.Frame
                            l_Frame_1.SongDifficultySection.Display.TextColor3 = v_u_11:singleton():get_difficulty_color_for_key(v_u_47)
                            l_Frame_1.SongDifficultySection.Display.Text = tostring(v_u_11:singleton():get_difficulty_for_key(v_u_47))
                            l_Frame_1.Check.Visible = v_u_12:songkey_include_reward(v_u_47) ~= true and true or v_u_13:get_song_key_owned_count(v_u_38, v_u_47) > 0
                            v_u_11:singleton():render_coverimage_for_key(l_Frame_1.Icon, l_Frame_1.IconOverlay, v_u_47)
                            v_u_52 = l_Frame_1.Background
                        end;
                        v51.set_selected = function(_, p53) --[[ Name: set_selected ]] --[[ Line: 191 ]]
                            --[[ Upvalues: (ref 1): v_u_52 ]]
                            if p53 then
                                v_u_52.Image = "rbxgameasset://Images/UIM_PlayOptions_SongContainerSelected"
                            else
                                v_u_52.Image = "rbxgameasset://Images/UIM_PlayOptions_SongContainer"
                            end;
                        end;
                        v51:cons()
                        return v51;
                    end)()
                    v_u_44:push_back(v_u_49)
                end;
            end;
        end;
        v_u_21.preview_songkey = function(_, p54) --[[ Name: preview_songkey ]] --[[ Line: 207 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_25, (ref 3): v_u_11, (ref 4): v_u_14, (copy 5): p_u_18, (ref 6): v_u_26 ]]
            v_u_24 = p54
            v_u_25.LoadedSection.Visible = true
            v_u_25.EmptySection.Visible = false
            local l_LoadedSection_0 = v_u_25.LoadedSection
            v_u_11:singleton():render_coverimage_for_key(l_LoadedSection_0.CoverBack.AlbumArt, l_LoadedSection_0.CoverBack.AlbumArtOverlay, v_u_24)
            v_u_14:render_songkey_colorsection(v_u_24, l_LoadedSection_0.CoverBack.ColorSection)
            l_LoadedSection_0.CoverBack.SongDifficultySection.Display.TextColor3 = v_u_11:singleton():get_difficulty_color_for_key(v_u_24)
            l_LoadedSection_0.CoverBack.SongDifficultySection.Display.Text = tostring(v_u_11:singleton():get_difficulty_for_key(v_u_24))
            l_LoadedSection_0.ArtistDisplay.Text = v_u_11:singleton():get_artist_for_key(v_u_24)
            l_LoadedSection_0.DescriptionDisplay.Text = v_u_11:singleton():get_description_for_key(v_u_24)
            l_LoadedSection_0.NameDisplay.Text = v_u_11:singleton():get_title_for_key(v_u_24)
            p_u_18._bgm_manager:preview_songkey(p54)
            v_u_26:set_visible(true)
        end;
        v_u_21.play_button_pressed = function(_) --[[ Name: play_button_pressed ]] --[[ Line: 225 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_11, (ref 3): v_u_6, (copy 4): p_u_18, (ref 5): v_u_15, (ref 6): v_u_17 ]]
            if v_u_24 == v_u_11:invalid_songkey() then
                return v_u_6:warnf("NewSongEventUI:play_button_pressed invalid songkey");
            end;
            local v55 = p_u_18._lobby_join:get_lobby()
            v55._game_join_protocol:set_event_info(v_u_15.EventMission.SongLaunchSpecialEvent)
            p_u_18._menus:push_menu(v_u_17:new(v55, p_u_18._spui, p_u_18._menus, v_u_24, nil))
        end;
        v_u_21.claim_reward_button_pressed = function(_) --[[ Name: claim_reward_button_pressed ]] --[[ Line: 236 ]]
            --[[ Upvalues: (copy 1): p_u_18, (ref 2): v_u_9, (ref 3): v_u_8, (copy 4): p_u_20, (copy 5): p_u_19, (ref 6): v_u_12, (ref 7): v_u_27, (ref 8): v_u_13 ]]
            local v_u_56 = p_u_18._menus:push_menu(v_u_9:new(p_u_18, p_u_18._spui, p_u_18._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_18._evt:wait_on_event_once(v_u_8.EVT_SongLaunchEvent_ClaimReward_Server, function(p57, p58) --[[ Line: 240 ]]
                --[[ Upvalues: (ref 1): p_u_18, (copy 2): v_u_56, (ref 3): p_u_20, (ref 4): v_u_9, (ref 5): p_u_19, (ref 6): v_u_12, (ref 7): v_u_27, (ref 8): v_u_13 ]]
                if p57 == true then
                    p_u_18._player_blob_manager:do_sync(function(_) --[[ Line: 246 ]]
                        --[[ Upvalues: (ref 1): p_u_18, (ref 2): v_u_56, (ref 3): v_u_9, (ref 4): v_u_12, (ref 5): v_u_27, (ref 6): v_u_13 ]]
                        p_u_18._menus:remove_menu(v_u_56)
                        p_u_18._menus:push_menu(v_u_9:new(p_u_18, p_u_18._spui, p_u_18._menus):set_text("Claimed Reward!", string.format("Got %d %s!", v_u_12:get_event_reward_currency_amount_for_event_id(v_u_27), v_u_13:currency_type_to_string(v_u_12:get_event_reward_currency_type_for_event_id(v_u_27)))))
                    end)
                else
                    p_u_18._menus:remove_menu(v_u_56)
                    p_u_20:push_menu(v_u_9:new(p_u_18, p_u_19, p_u_20):set_text("Failed", p58))
                end;
            end)
            p_u_18._evt:fire_event_to_server(v_u_8.EVT_SongLaunchEvent_ClaimReward_Client)
        end;
        v_u_21.layout = function(_) --[[ Name: layout ]] --[[ Line: 259 ]]
            --[[ Upvalues: (copy 1): p_u_19, (copy 2): v_u_21, (ref 3): v_u_23, (ref 4): v_u_22 ]]
            p_u_19:uiobj_rescale_to_max_nxy(v_u_21, 0.9, 0.9, v_u_23)
            v_u_22:SetPrimaryPartCFrame(p_u_19:get_cframe({
                ["PositionNXY"] = Vector2.new(0.5, 0.5),
                ["OffsetXYZ"] = v_u_21:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            }))
        end;
        v_u_21.behaviour_update = function(_, p59, p60) --[[ Name: behaviour_update ]] --[[ Line: 268 ]]
            --[[ Upvalues: (copy 1): v_u_21 ]]
            v_u_21:behaviour_update_base(p59, p60)
        end;
        v_u_21.visual_update = function(_, p61, p62) --[[ Name: visual_update ]] --[[ Line: 272 ]]
            --[[ Upvalues: (copy 1): v_u_21 ]]
            v_u_21:visual_update_base(p61, p62)
        end;
        v_u_21.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 276 ]]
            --[[ Upvalues: (copy 1): p_u_18, (ref 2): v_u_22 ]]
            p_u_18._bgm_manager:stop_song_preview()
            v_u_22:Destroy()
        end;
        local v_u_63 = -1
        v_u_21.set_alpha = function(_, p64, p65) --[[ Name: set_alpha ]] --[[ Line: 282 ]]
            --[[ Upvalues: (ref 1): v_u_63, (ref 2): v_u_1, (ref 3): v_u_22 ]]
            if v_u_63 ~= p64 or p65 == true then
                v_u_63 = p64
                v_u_1:r_set_alpha(v_u_22, v_u_63)
            end;
        end;
        v_u_21.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 289 ]]
            --[[ Upvalues: (ref 1): v_u_63 ]]
            return v_u_63;
        end;
        v_u_21.set_scale = function(_, p66) --[[ Name: set_scale ]] --[[ Line: 290 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            v_u_23 = p66
        end;
        v_u_21.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 291 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            return v_u_23;
        end;
        v_u_21.get_native_size = function(_) --[[ Name: get_native_size ]] --[[ Line: 292 ]]
            --[[ Upvalues: (copy 1): v_u_21 ]]
            return v_u_21._native_size;
        end;
        v_u_21.get_size = function(_) --[[ Name: get_size ]] --[[ Line: 293 ]]
            --[[ Upvalues: (copy 1): v_u_21 ]]
            return v_u_21._size;
        end;
        v_u_21.set_size = function(_, p67) --[[ Name: set_size ]] --[[ Line: 294 ]]
            --[[ Upvalues: (copy 1): v_u_21, (ref 2): v_u_22 ]]
            v_u_21._size = p67
            v_u_22.PrimaryPart.Size = Vector3.new(p67.X, p67.Y, 0)
        end;
        v_u_21.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 298 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            return v_u_22.PrimaryPart.Position;
        end;
        v_u_21.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 299 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            return v_u_22.PrimaryPart.SurfaceGui;
        end;
        v_u_21.set_showing = function(_, p68) --[[ Name: set_showing ]] --[[ Line: 300 ]]
            --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_10 ]]
            if p68 then
                v_u_22.Parent = v_u_10:get_world_ui_folder()
            else
                v_u_22.Parent = nil
            end;
        end;
        v_u_21:cons()
        return v_u_21;
    end
};
