-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:40 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_7 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Local.GameJoinProtocol)
require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_8 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_9 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_10 = require(game.ReplicatedStorage.Lobby.UI.ChatUISection)
local v_u_11 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_12 = require(game.ReplicatedStorage.LocalShared.BGMManager)
local v_u_13 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_14 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_15 = require(game.ReplicatedStorage.Lobby.Menus.GameStartV2UI)
return {
    ["new"] = function(_, p_u_16, p_u_17, p_u_18) --[[ Name: new ]] --[[ Line: 25 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_2, (copy 3): v_u_3, (copy 4): v_u_1, (copy 5): v_u_11, (copy 6): v_u_10, (copy 7): v_u_12, (copy 8): v_u_8, (copy 9): v_u_6, (copy 10): v_u_5, (copy 11): v_u_7, (copy 12): v_u_14, (copy 13): v_u_9, (copy 14): v_u_13, (copy 15): v_u_15 ]]
        local v19 = v_u_4:new(p_u_17, p_u_18)
        local v_u_20 = nil
        local v_u_21 = 1
        local v_u_22 = 1
        local l__game_join_protocol_0 = p_u_16._game_join_protocol
        local v_u_23 = nil
        local v_u_24 = v_u_2:new()
        local v_u_25 = v_u_3:new()
        local v_u_26 = nil
        local v_u_27 = nil
        local v_u_28 = false
        local v_u_29 = nil
        v19.cons = function(p30) --[[ Name: cons ]] --[[ Line: 48 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_1, (ref 3): v_u_11, (copy 4): l__game_join_protocol_0, (ref 5): v_u_23, (ref 6): v_u_27, (ref 7): v_u_29, (ref 8): v_u_10, (copy 9): p_u_16, (copy 10): p_u_17 ]]
            v_u_20 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.VotePickV2UI:Clone()
            v_u_20.Name = v_u_1:gen_name(v_u_20.Name)
            v_u_20.Parent = v_u_11:get_world_ui_folder()
            p30._native_size = v_u_20.PrimaryPart.Size
            p30._size = p30._native_size
            l__game_join_protocol_0:begin_votepick()
            v_u_23 = v_u_20.SongButtonProto
            v_u_23.Parent = nil
            v_u_27 = v_u_20.MainSurface.SurfaceGui.Frame.TimeDisplaySection.Display
            p30:initialize_vote_buttons()
            p30:update_vote_labels()
            v_u_29 = v_u_10:new(p_u_16, p_u_17, p30, v_u_20.MainSurface.SurfaceGui.Frame.ChatSection.ChatTextFrameOutline.ChatTextFrame, v_u_20.MainSurface.SurfaceGui.Frame.ChatSection.ChatBarFrame)
            p30:reset_selected_item()
            p30:transition_update_visual(0)
            p30:layout()
        end;
        v19.handles_bgm = function(_) --[[ Name: handles_bgm ]] --[[ Line: 82 ]]
            return true;
        end;
        v19.on_pushed_to_stack_top = function(_) --[[ Name: on_pushed_to_stack_top ]] --[[ Line: 83 ]]
            --[[ Upvalues: (copy 1): p_u_16, (ref 2): v_u_12 ]]
            p_u_16._bgm_manager:play_bgm(v_u_12.BGM_MATCHMAKING)
        end;
        v19.initialize_vote_buttons = function(p_u_31) --[[ Name: initialize_vote_buttons ]] --[[ Line: 87 ]]
            --[[ Upvalues: (copy 1): l__game_join_protocol_0, (ref 2): v_u_23, (ref 3): v_u_20, (ref 4): v_u_8, (copy 5): v_u_24, (ref 6): v_u_1, (ref 7): v_u_6, (ref 8): v_u_5, (copy 9): p_u_17, (ref 10): v_u_7, (ref 11): v_u_21, (copy 12): v_u_25, (copy 13): p_u_16, (ref 14): v_u_26 ]]
            local v_u_32 = l__game_join_protocol_0:get_votepick_items()
            for v_u_33 = 1, #v_u_32 do
                local v_u_34 = v_u_23:Clone()
                v_u_34.Parent = v_u_20
                v_u_34.Name = string.format("VoteButton(%d)", v_u_33)
                v_u_34.Position = v_u_20.Anchors:FindFirstChild(string.format("Slot%d", v_u_33)).Anchor.Position
                local v35 = v_u_32[v_u_33]
                v_u_34.SurfaceGui.Frame.Pane.DifficultyFrame.DifficultyDisplay.Text = string.format("%d", v_u_8:singleton():get_difficulty_for_key(v35))
                v_u_8:singleton():render_coverimage_for_key(v_u_34.SurfaceGui.Frame.Pane.AlbumArt, v_u_34.SurfaceGui.Frame.Pane.AlbumArt.AlbumArtOverlay, v35)
                v_u_34.SurfaceGui.Frame.Pane.SongNameDisplay.Text = v_u_8:singleton():get_title_for_key(v35)
                v_u_24:add(v_u_32[v_u_33], v_u_34.SurfaceGui.Frame.Pane.VoteCountDisplay)
                local v_u_36 = 1
                local v_u_37 = v_u_1:get_list_of_children_of_classname(v_u_34, "ImageLabel")
                local v_u_38 = v_u_1:get_list_of_children_of_classname(v_u_34, "TextLabel")
                local v41 = v_u_6:new(v_u_5:new(p_u_31, v_u_20.PrimaryPart, v_u_34), p_u_17, function() --[[ Line: 112 ]]
                    --[[ Upvalues: (copy 1): p_u_31, (copy 2): v_u_32, (copy 3): v_u_33 ]]
                    p_u_31:vote_for_songkey(v_u_32[v_u_33])
                end):set_enabled_anim_updatefn(function(_, p39) --[[ Line: 115 ]]
                    --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_36, (ref 3): v_u_1, (copy 4): v_u_37, (copy 5): v_u_38, (copy 6): v_u_34, (ref 7): v_u_21 ]]
                    local v40 = v_u_7:YForPointOf2PtLine(Vector2.new(0, 0.25), Vector2.new(1, 1), p39)
                    if v_u_36 ~= v40 then
                        v_u_36 = v40
                        v_u_1:list_set_alpha_name(v_u_37, {
                            ["ImageAlpha"] = v_u_36
                        })
                        v_u_1:list_set_alpha_name(v_u_38, {
                            ["TextAlpha"] = v_u_36
                        })
                        v_u_1:r_set_alpha(v_u_34, v_u_21)
                    end;
                end):set_auto_zoffset_behaviour(true)
                v_u_25:push_back(v41)
                p_u_31:add_cycle_element(p_u_16, 1, v41)
            end;
            local v_u_42 = 1
            local v_u_43 = v_u_1:get_list_of_children_of_classname(v_u_20.RandomButton, "ImageLabel")
            local v_u_44 = v_u_1:get_list_of_children_of_classname(v_u_20.RandomButton, "TextLabel")
            v_u_26 = v_u_6:new(v_u_5:new(p_u_31, v_u_20.PrimaryPart, v_u_20.RandomButton), p_u_17, function() --[[ Line: 136 ]]
                --[[ Upvalues: (copy 1): p_u_31 ]]
                p_u_31:vote_for_random()
            end):set_enabled_anim_updatefn(function(_, p45) --[[ Line: 139 ]]
                --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_42, (ref 3): v_u_1, (copy 4): v_u_43, (copy 5): v_u_44, (ref 6): v_u_20, (ref 7): v_u_21 ]]
                local v46 = v_u_7:YForPointOf2PtLine(Vector2.new(0, 0.25), Vector2.new(1, 1), p45)
                if v_u_42 ~= v46 then
                    v_u_42 = v46
                    v_u_1:list_set_alpha_name(v_u_43, {
                        ["ImageAlpha"] = v_u_42
                    })
                    v_u_1:list_set_alpha_name(v_u_44, {
                        ["TextAlpha"] = v_u_42
                    })
                    v_u_1:r_set_alpha(v_u_20.RandomButton, v_u_21)
                end;
            end)
            p_u_31:add_cycle_element(p_u_16, 1, v_u_26)
        end;
        v19.vote_for_songkey = function(p47, p48) --[[ Name: vote_for_songkey ]] --[[ Line: 183 ]]
            --[[ Upvalues: (copy 1): p_u_16, (ref 2): v_u_14, (copy 3): l__game_join_protocol_0, (ref 4): v_u_28 ]]
            p_u_16._sfx_manager:play_sfx(v_u_14.SFX_BUTTONPRESS)
            l__game_join_protocol_0:votepick_for_key(p48)
            v_u_28 = true
            p47:disable_buttons()
        end;
        v19.vote_for_random = function(p49) --[[ Name: vote_for_random ]] --[[ Line: 190 ]]
            --[[ Upvalues: (copy 1): l__game_join_protocol_0, (ref 2): v_u_1 ]]
            local v50 = l__game_join_protocol_0:get_votepick_items()
            p49:vote_for_songkey(v50[v_u_1:rand_rangei(1, #v50 + 1)])
        end;
        v19.disable_buttons = function(_) --[[ Name: disable_buttons ]] --[[ Line: 195 ]]
            --[[ Upvalues: (copy 1): v_u_25, (ref 2): v_u_26 ]]
            for v51 = 1, v_u_25:count() do
                v_u_25:get(v51):set_enabled(false)
            end;
            v_u_26:set_enabled(false)
        end;
        local l_VOTEPICK_TIMEOUT_MS_0 = v_u_9.VOTEPICK_TIMEOUT_MS
        local v_u_52 = -1
        v19.update_vote_labels = function(_) --[[ Name: update_vote_labels ]] --[[ Line: 204 ]]
            --[[ Upvalues: (copy 1): l__game_join_protocol_0, (ref 2): v_u_52, (ref 3): v_u_2, (ref 4): l_VOTEPICK_TIMEOUT_MS_0, (ref 5): v_u_13, (ref 6): v_u_1, (copy 7): v_u_24 ]]
            if l__game_join_protocol_0:last_updated_time() ~= v_u_52 then
                v_u_52 = l__game_join_protocol_0:last_updated_time()
                local v53 = v_u_2:new()
                local v54 = l__game_join_protocol_0:get_slots()
                local v55 = v54:get(l__game_join_protocol_0:get_slot())
                if v55 ~= nil then
                    l_VOTEPICK_TIMEOUT_MS_0 = v55._timeout
                end;
                local v56 = 0
                local v57 = 0
                for v58 = 1, 4 do
                    if v54:contains(v58) then
                        local v59 = v54:get(v58)
                        local l__votepick_song_key_0 = v59._votepick_song_key
                        if l__votepick_song_key_0 ~= nil then
                            if v53:contains(l__votepick_song_key_0) then
                                v53:add(l__votepick_song_key_0, v53:get(l__votepick_song_key_0) + 1)
                            else
                                v53:add(l__votepick_song_key_0, 1)
                            end;
                        end;
                        if v59._match_mode == v_u_13.Compete then
                            v56 = v56 + 1
                        else
                            v57 = v57 + 1
                        end;
                        local _ = v59._id == v_u_1:get_local_userid()
                    end;
                end;
                local v60 = l__game_join_protocol_0:get_votepick_items()
                for v61 = 1, #v60 do
                    local v62 = v60[v61]
                    if v_u_24:contains(v62) then
                        local v63 = v_u_24:get(v62)
                        if v53:contains(v62) then
                            v63.Text = string.format("%d", v53:get(v62))
                        else
                            v63.Text = "0"
                        end;
                    end;
                end;
            end;
        end;
        v19.behaviour_update = function(p64, p65, p66) --[[ Name: behaviour_update ]] --[[ Line: 267 ]]
            --[[ Upvalues: (ref 1): l_VOTEPICK_TIMEOUT_MS_0, (ref 2): v_u_7, (ref 3): v_u_27, (ref 4): v_u_29, (copy 5): l__game_join_protocol_0, (copy 6): p_u_18, (ref 7): v_u_15, (copy 8): p_u_16, (copy 9): p_u_17 ]]
            p64:behaviour_update_base(p65, p66)
            p64:update_vote_labels()
            l_VOTEPICK_TIMEOUT_MS_0 = l_VOTEPICK_TIMEOUT_MS_0 - v_u_7:TimescaleToDeltaTime(p65) * 1000
            if l_VOTEPICK_TIMEOUT_MS_0 < 0 then
                l_VOTEPICK_TIMEOUT_MS_0 = 0
            end;
            v_u_27.Text = string.format("%d", (math.floor(l_VOTEPICK_TIMEOUT_MS_0 / 1000)))
            v_u_29:behaviour_update(p65)
            if l__game_join_protocol_0:notify_client_do_preload() then
                p_u_18:remove_all_menus()
                p_u_18:push_menu(v_u_15:new(p_u_16, p_u_17, p_u_18, p_u_16._game_join_protocol))
            end;
        end;
        v19.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 286 ]]
            --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_20 ]]
            v_u_29:cleanup()
            v_u_20:Destroy()
        end;
        v19.layout = function(p67) --[[ Name: layout ]] --[[ Line: 291 ]]
            --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_22, (ref 3): v_u_20 ]]
            p_u_17:uiobj_rescale_to_max_nxy(p67, 0.95, 0.95, v_u_22)
            v_u_20:SetPrimaryPartCFrame(p_u_17:get_cframe({
                ["PositionNXY"] = Vector2.new(0.5, 0.5),
                ["OffsetXYZ"] = p67:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            }))
        end;
        v19.visual_update = function(p68, p69, p70) --[[ Name: visual_update ]] --[[ Line: 300 ]]
            p68:visual_update_base(p69, p70)
        end;
        v19.set_alpha = function(_, p71) --[[ Name: set_alpha ]] --[[ Line: 304 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_1, (ref 3): v_u_20 ]]
            if v_u_21 ~= p71 then
                v_u_21 = p71
                v_u_1:r_set_alpha(v_u_20, v_u_21)
            end;
        end;
        v19.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 310 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            return v_u_21;
        end;
        v19.set_scale = function(_, p72) --[[ Name: set_scale ]] --[[ Line: 311 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            v_u_22 = p72
        end;
        v19.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 312 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            return v_u_22;
        end;
        v19.get_native_size = function(p73) --[[ Name: get_native_size ]] --[[ Line: 314 ]]
            return p73._native_size;
        end;
        v19.get_size = function(p74) --[[ Name: get_size ]] --[[ Line: 317 ]]
            return p74._size;
        end;
        v19.set_size = function(p75, p76) --[[ Name: set_size ]] --[[ Line: 320 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            p75._size = p76
            v_u_20.PrimaryPart.Size = Vector3.new(p76.X, p76.Y, 0)
        end;
        v19.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 324 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20.PrimaryPart.Position;
        end;
        v19.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 327 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20.PrimaryPart.SurfaceGui;
        end;
        v19:cons()
        return v19;
    end
};
