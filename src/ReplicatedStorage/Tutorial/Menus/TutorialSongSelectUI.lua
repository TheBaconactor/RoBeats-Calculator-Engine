-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:15 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.SPVector)
local v_u_8 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_9 = require(game.ReplicatedStorage.Menu.SPUIDisplay)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_10 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_11 = require(game.ReplicatedStorage.Tutorial.UI.TutorialSongSelectElement)
local v_u_12 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_13 = require(game.ReplicatedStorage.Tutorial.TutorialData)
local v_u_14 = require(game.ReplicatedStorage.Menu.CharacterDialogue)
return {
    ["new"] = function(_, p_u_15, p_u_16, p_u_17, p_u_18) --[[ Name: new ]] --[[ Line: 24 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_13, (copy 4): v_u_12, (copy 5): v_u_9, (copy 6): v_u_4, (copy 7): v_u_14, (copy 8): v_u_1, (copy 9): v_u_5, (copy 10): v_u_10, (copy 11): v_u_11, (copy 12): v_u_8, (copy 13): v_u_6, (copy 14): v_u_7 ]]
        local v19 = v_u_3:new(p_u_16, p_u_17)
        local v_u_20 = nil
        local v_u_21 = 1
        local v_u_22 = 1
        local v_u_23 = nil
        local v_u_24 = nil
        local v_u_25 = nil
        local v_u_26 = nil
        local v_u_27 = nil
        local v_u_28 = v_u_2:new()
        local v_u_29 = nil
        local v_u_30 = nil
        v19.cons = function(p_u_31) --[[ Name: cons ]] --[[ Line: 43 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_20, (ref 3): v_u_12, (ref 4): v_u_23, (ref 5): v_u_9, (copy 6): p_u_16, (ref 7): v_u_24, (ref 8): v_u_4, (ref 9): v_u_26, (ref 10): v_u_14, (ref 11): v_u_25, (ref 12): v_u_29, (ref 13): v_u_2, (ref 14): v_u_1, (ref 15): v_u_30, (copy 16): p_u_15, (ref 17): v_u_5, (ref 18): v_u_10 ]]
            v_u_13:set_camera_start()
            v_u_20 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.TutorialSongSelectUI:Clone()
            v_u_20.Parent = v_u_12:get_world_ui_folder()
            p_u_31._native_size = v_u_20.PrimaryPart.Size
            p_u_31._size = p_u_31._native_size
            v_u_23 = v_u_9:new(v_u_20.TutorialCharacter, p_u_16):set_position_nxy(0.15, 1):set_anchor_rnxy(0.5, 1)
            v_u_24 = v_u_4:new(v_u_23, v_u_23:get_part(), v_u_20.DialogueBubble):set_child_relative_xy(v_u_23:get_size().X * 0.05, v_u_23:get_size().Y * 0.7)
            v_u_26 = v_u_14:new("Starlet", v_u_20.DialogueBubble, v_u_24)
            v_u_26:display_text("Let\'s start out with some easy songs. Pick 3 out of this list.\nGot any favorites?")
            v_u_25 = v_u_9:new(v_u_20.SelectionSurface, p_u_16, true):set_position_nxy(0.55, 0.45):set_anchor_rnxy(0.5, 0.5)
            v_u_29 = v_u_20.SelectionSurface.PrimaryPart.SurfaceGui.Frame.PreviewDisplay
            v_u_29.Text = ""
            p_u_31:setup_selection_elements()
            local v_u_32 = v_u_2:new()
            v_u_32:push_back(v_u_20.PlayButtonSurface.SurfaceGui.Frame.Back)
            v_u_32:push_back(v_u_20.PlayButtonSurface.SurfaceGui.Frame.Back2)
            v_u_32:push_back(v_u_20.PlayButtonSurface.SurfaceGui.Frame.Back2.Text)
            v_u_32:push_back(v_u_20.PlayButtonSurface.SurfaceGui.Frame.ReadyDown)
            v_u_32:push_back(v_u_20.PlayButtonSurface.SurfaceGui.Frame.ReadyUp)
            local function f_set_play_button_alpha(p33) --[[ Name: set_play_button_alpha ]] --[[ Line: 84 ]]
                --[[ Upvalues: (copy 1): v_u_32, (ref 2): v_u_1 ]]
                for v34 = 1, v_u_32:count() do
                    local v35 = v_u_32:get(v34)
                    v35.ImageTransparency = v_u_1:tra(p33)
                    v35.Name = v_u_1:r_set_alpha_generate_name({
                        ["ImageAlpha"] = p33
                    }, v35)
                end;
            end;
            f_set_play_button_alpha(0)
            v_u_30 = p_u_31:add_cycle_element(p_u_15, 1, v_u_5:new(v_u_4:new(v_u_25, v_u_25:get_part(), v_u_20.PlayButtonSurface):set_child_relative_xy(v_u_25:get_size().X * 0.575, -v_u_25:get_size().Y * 0.51), p_u_16, function() --[[ Line: 102 ]]
                --[[ Upvalues: (ref 1): p_u_15, (ref 2): v_u_10, (copy 3): p_u_31 ]]
                p_u_15._sfx_manager:play_sfx(v_u_10.SFX_MENU_OPEN_LONG)
                p_u_31:on_play_pressed()
            end):set_passive_anim():set_enabled_anim_updatefn(function(_, p36) --[[ Line: 106 ]]
                --[[ Upvalues: (ref 1): v_u_30, (copy 2): f_set_play_button_alpha ]]
                v_u_30:set_scale(p36 + 0.15)
                f_set_play_button_alpha(p36)
            end):set_enabled(false, true))
            p_u_31:reset_selected_item()
            p_u_31:transition_update_visual(0)
            p_u_31:layout()
        end;
        local v_u_37 = v_u_2:new()
        v19.setup_selection_elements = function(p_u_38) --[[ Name: setup_selection_elements ]] --[[ Line: 119 ]]
            --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_20, (copy 3): v_u_37, (copy 4): p_u_18, (ref 5): v_u_11, (ref 6): v_u_4, (ref 7): v_u_25, (copy 8): p_u_16, (copy 9): p_u_15, (ref 10): v_u_10, (copy 11): v_u_28 ]]
            v_u_27 = v_u_20.SelectionElementProto
            v_u_27.Parent = nil
            for v39 = 1, 9 do
                local v40 = v_u_20.SelectionSurface.Anchors:FindFirstChild(string.format("Anchor%d", v39))
                v40.Parent = nil
                v_u_37:push_back(v40)
            end;
            for v41 = 1, p_u_18:count() do
                local v_u_42 = p_u_18:get(v41)
                local v43 = v_u_37:get(v41)
                local v44 = v_u_27:Clone()
                v44.Name = string.format("TutorialSongSelectElement(%d)", v41)
                v44.Parent = v_u_20
                local v_u_45 = nil
                v_u_45 = v_u_11:new(v_u_4:new(v_u_25, v_u_25:get_part(), v44), p_u_16, function() --[[ Line: 139 ]]
                    --[[ Upvalues: (ref 1): v_u_45, (copy 2): p_u_38, (ref 3): p_u_15, (ref 4): v_u_10, (copy 5): v_u_42 ]]
                    local v46 = not v_u_45:get_item_selected()
                    if v46 == true and p_u_38:get_item_selected_count() >= p_u_38:get_max_item_selected_count() then
                        p_u_15._sfx_manager:play_sfx(v_u_10.SFX_MENU_CLOSE)
                        return;
                    else
                        v_u_45:set_item_selected(v46)
                        if v_u_45:get_item_selected() == true then
                            p_u_15._bgm_manager:preview_songkey(v_u_42)
                            p_u_15._sfx_manager:play_sfx(v_u_10.SFX_MENU_OPEN)
                        else
                            p_u_15._sfx_manager:play_sfx(v_u_10.SFX_MENU_CLOSE)
                        end;
                    end;
                end)
                v_u_45:set_song_key(v_u_42)
                v_u_45:set_position(v43.Position)
                p_u_38:add_cycle_element(p_u_15, 1, v_u_45)
                v_u_28:push_back(v_u_45)
            end;
        end;
        v19.get_item_selected_count = function(_) --[[ Name: get_item_selected_count ]] --[[ Line: 163 ]]
            --[[ Upvalues: (copy 1): v_u_28 ]]
            local v47 = 0
            for v48 = 1, v_u_28:count() do
                if v_u_28:get(v48):get_item_selected() == true then
                    v47 = v47 + 1
                end;
            end;
            return v47;
        end;
        v19.get_max_item_selected_count = function(_) --[[ Name: get_max_item_selected_count ]] --[[ Line: 173 ]]
            return 3;
        end;
        v19.on_play_pressed = function(p_u_49) --[[ Name: on_play_pressed ]] --[[ Line: 177 ]]
            --[[ Upvalues: (ref 1): v_u_8, (copy 2): p_u_17, (ref 3): v_u_6, (copy 4): p_u_15, (copy 5): p_u_16, (ref 6): v_u_2, (copy 7): v_u_28 ]]
            if p_u_49:get_item_selected_count() == 0 then
                v_u_8:errf("TutorialSongSelectUI:on_play_pressed selected item count is 0")
            end;
            local v_u_50 = p_u_17:push_menu(v_u_6:new(p_u_15, p_u_16, p_u_17):set_text("Connecting...", "Please wait..."):set_close_button_visible(false))
            local v51 = v_u_2:new()
            for v52 = 1, v_u_28:count() do
                local v53 = v_u_28:get(v52)
                if v53:get_item_selected() == true then
                    v51:push_back(v53:get_song_key())
                    p_u_15._player_blob_manager:add_recently_acquired_songid(v53:get_song_key())
                end;
            end;
            p_u_15._tutorial_manager:song_select_notify_server(v51, function() --[[ Line: 197 ]]
                --[[ Upvalues: (ref 1): p_u_17, (copy 2): v_u_50, (copy 3): p_u_49 ]]
                p_u_17:remove_menu(v_u_50)
                p_u_17:remove_menu(p_u_49)
            end)
        end;
        v19.layout = function(_) --[[ Name: layout ]] --[[ Line: 203 ]]
            --[[ Upvalues: (copy 1): p_u_16, (ref 2): v_u_25, (ref 3): v_u_22, (ref 4): v_u_23, (ref 5): v_u_26 ]]
            p_u_16:uiobj_rescale_to_max_nxy(v_u_25, 0.6, 0.7, v_u_22)
            v_u_25:layout()
            p_u_16:uiobj_rescale_to_max_nxy(v_u_23, 0.2, 0.5, v_u_22)
            v_u_23:layout()
            v_u_26:layout()
        end;
        v19.visual_update = function(p54, p55, _) --[[ Name: visual_update ]] --[[ Line: 212 ]]
            --[[ Upvalues: (copy 1): p_u_15 ]]
            p54:visual_update_base(p55, p_u_15)
        end;
        v19.behaviour_update = function(p56, p57, _) --[[ Name: behaviour_update ]] --[[ Line: 216 ]]
            --[[ Upvalues: (copy 1): p_u_15, (ref 2): v_u_30, (ref 3): v_u_26, (ref 4): v_u_7, (ref 5): v_u_29 ]]
            p56:behaviour_update_base(p57, p_u_15)
            if p56:get_item_selected_count() >= p56:get_max_item_selected_count() then
                v_u_30:set_enabled(true)
            else
                v_u_30:set_enabled(false)
            end;
            v_u_26:update(p57)
            local v58 = p_u_15._bgm_manager:get_preview_songkey()
            local v59 = p_u_15._bgm_manager:is_preview_song_loading() or p_u_15._bgm_manager:is_preview_transitioning()
            local v60 = v_u_7:singleton():contains_key(v58)
            if v59 then
                v_u_29.Text = "Loading..."
                return;
            elseif v60 then
                v_u_29.Text = "Now Playing: " .. v_u_7:singleton():get_title_for_key(v58)
            else
                v_u_29.Text = "Click on the song to play preview!"
            end;
        end;
        v19.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 239 ]]
            --[[ Upvalues: (copy 1): p_u_15, (ref 2): v_u_20 ]]
            p_u_15._bgm_manager:stop_song_preview()
            v_u_20:Destroy()
        end;
        v19.set_alpha = function(_, p61) --[[ Name: set_alpha ]] --[[ Line: 244 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_1, (ref 3): v_u_20 ]]
            if v_u_21 ~= p61 then
                v_u_21 = p61
                v_u_1:r_set_alpha(v_u_20, v_u_21)
            end;
        end;
        v19.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 250 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            return v_u_21;
        end;
        v19.set_scale = function(_, p62) --[[ Name: set_scale ]] --[[ Line: 251 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            v_u_22 = p62
        end;
        v19.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 252 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            return v_u_22;
        end;
        v19.get_native_size = function(p63) --[[ Name: get_native_size ]] --[[ Line: 254 ]]
            return p63._native_size;
        end;
        v19.get_size = function(p64) --[[ Name: get_size ]] --[[ Line: 257 ]]
            return p64._size;
        end;
        v19.set_size = function(p65, p66) --[[ Name: set_size ]] --[[ Line: 260 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            p65._size = p66
            v_u_20.PrimaryPart.Size = Vector3.new(p66.X, p66.Y, 0)
        end;
        v19.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 264 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20.PrimaryPart.Position;
        end;
        v19.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 267 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20.PrimaryPart.SurfaceGui;
        end;
        v19:cons()
        return v19;
    end
};
