-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:41 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_2 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_6 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_7 = require(game.ReplicatedStorage.Menu.CharacterDialogue)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_9 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_10 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
return {
    ["new"] = function(_, p_u_12, p_u_13, p_u_14, p_u_15) --[[ Name: new ]] --[[ Line: 19 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_6, (copy 3): v_u_4, (copy 4): v_u_3, (copy 5): v_u_7, (copy 6): v_u_5, (copy 7): v_u_9, (copy 8): v_u_10, (copy 9): v_u_11, (copy 10): v_u_8, (copy 11): v_u_1 ]]
        local v16 = v_u_2:new(p_u_13, p_u_14)
        local v_u_17 = nil
        local v_u_18 = 1
        local v_u_19 = 1
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = nil
        local v_u_23 = nil
        local v_u_24 = nil
        local v_u_25 = nil
        v16.cons = function(p_u_26) --[[ Name: cons ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_6, (copy 3): p_u_12, (ref 4): v_u_4, (ref 5): v_u_3, (copy 6): p_u_13, (ref 7): v_u_22, (ref 8): v_u_7, (ref 9): v_u_21, (ref 10): v_u_5, (ref 11): v_u_24, (ref 12): v_u_25, (ref 13): v_u_23, (copy 14): p_u_15 ]]
            v_u_17 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.MatchLeavePenaltyUI:Clone()
            v_u_17.Parent = v_u_6:get_world_ui_folder()
            p_u_26._native_size = v_u_17.PrimaryPart.Size
            p_u_26._size = p_u_26._native_size
            p_u_26:add_cycle_element(p_u_12, 1, v_u_4:new(v_u_3:new(p_u_26, v_u_17.PrimaryPart, v_u_17.BackButtonSurface), p_u_13, function() --[[ Line: 46 ]]
                --[[ Upvalues: (copy 1): p_u_26 ]]
                p_u_26:on_close()
            end))
            v_u_22 = v_u_7:new("Roxie", v_u_17.RoxieDialogue, v_u_3:new(p_u_26, v_u_17.PrimaryPart, v_u_17.RoxieDialogue))
            v_u_21 = p_u_26:add_cycle_element(p_u_12, 1, v_u_4:new(v_u_3:new(p_u_26, v_u_17.PrimaryPart, v_u_17.Roxie), p_u_12._spui, function() --[[ Line: 60 ]]
                --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_5, (ref 3): v_u_22 ]]
                p_u_12._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
                v_u_22:display_text("Whatever the story is...\nJust make sure it doesn\'t happen again, okay?")
            end):set_selected_tar_scale(1.05):set_triggered_scale_offset(0.1))
            v_u_24 = p_u_26:add_cycle_element(p_u_12, 1, v_u_4:new(v_u_3:new(p_u_26, v_u_17.PrimaryPart, v_u_17.PlayButtonSurface), p_u_13, function() --[[ Line: 69 ]]
                --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_5, (ref 3): v_u_25 ]]
                p_u_12._sfx_manager:play_sfx(v_u_5.SFX_MENU_OPEN_LONG)
                if v_u_25 ~= nil then
                    v_u_25()
                    v_u_25 = nil
                end;
            end))
            v_u_24:set_visible(false)
            local v27 = p_u_26:add_cycle_element(p_u_12, 1, v_u_4:new(v_u_3:new(p_u_26, v_u_17.PrimaryPart, v_u_17.SorryButton), p_u_13, function() --[[ Line: 82 ]]
                --[[ Upvalues: (copy 1): p_u_26 ]]
                p_u_26:sorry_button_pressed()
            end))
            local l_Frame_0 = v_u_17.PrimaryPart.SurfaceGui.Frame
            local l_SubPenalized_0 = l_Frame_0.SubPenalized
            local l_SubNotPenalized_0 = l_Frame_0.SubNotPenalized
            local l_Timer_0 = l_Frame_0.Timer
            v_u_23 = l_Timer_0.TimerDisplay
            if p_u_15 then
                v_u_22:display_text("Leaving mid match, over and over again?\nI\'m disappointed in you.\nSo, if you\'re really THAT sorry... Then pay up!\n ...And I\'ll look the other way. This time.")
                l_SubPenalized_0.Visible = true
                l_SubNotPenalized_0.Visible = false
                l_Timer_0.Visible = true
                v27:set_visible(true)
            else
                v_u_22:display_text("Internet cut out? Trip over the power cable?\nWe all make mistakes. And it\'s okay!\nSince it\'s the first time, I\'ll let it slide.\nJust make sure it doesn\'t happen again!")
                l_SubPenalized_0.Visible = false
                l_SubNotPenalized_0.Visible = true
                l_Timer_0.Visible = false
                v27:set_visible(false)
            end;
            p_u_26:reset_selected_item()
            p_u_26:transition_update_visual(0)
            p_u_26:layout()
        end;
        v16.set_on_close_fn = function(p28, p29) --[[ Name: set_on_close_fn ]] --[[ Line: 117 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            v_u_20 = p29
            return p28;
        end;
        v16.on_close = function(p30) --[[ Name: on_close ]] --[[ Line: 122 ]]
            --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_5, (ref 3): v_u_20, (copy 4): p_u_14 ]]
            if p_u_12 ~= nil then
                p_u_12._sfx_manager:play_sfx(v_u_5.SFX_MENU_CLOSE)
            end;
            if v_u_20 ~= nil then
                v_u_20()
                v_u_20 = nil
            end;
            p_u_14:remove_menu(p30)
        end;
        v16.set_on_play_fn = function(p31, p32) --[[ Name: set_on_play_fn ]] --[[ Line: 133 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_25 ]]
            v_u_24:set_visible(true)
            v_u_25 = p32
            return p31;
        end;
        v16.sorry_button_pressed = function(p_u_33) --[[ Name: sorry_button_pressed ]] --[[ Line: 139 ]]
            --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_9, (copy 3): p_u_12, (copy 4): p_u_13, (ref 5): v_u_10, (ref 6): v_u_11 ]]
            local v_u_34 = p_u_14:push_menu(v_u_9:new(p_u_12, p_u_13, p_u_14):set_text("...", "Loading..."):set_title_sub_visible(false))
            p_u_12._evt:wait_on_event_once(v_u_10.EVT_MatchLeavePenalty_ServerRespondRequiredProductID, function(p35) --[[ Line: 146 ]]
                --[[ Upvalues: (ref 1): v_u_11, (ref 2): p_u_14, (copy 3): p_u_33, (copy 4): v_u_34, (ref 5): p_u_12, (ref 6): v_u_9, (ref 7): p_u_13 ]]
                if p35 == v_u_11.ProductID_None then
                    p_u_14:remove_menu(p_u_33)
                    p_u_14:remove_menu(v_u_34)
                else
                    p_u_12._player_blob_manager:set_iap_finish_fn(function() --[[ Line: 154 ]]
                        --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_34, (ref 3): v_u_9, (ref 4): p_u_12, (ref 5): p_u_13, (ref 6): p_u_33 ]]
                        p_u_14:remove_menu(v_u_34)
                        p_u_14:push_menu(v_u_9:new(p_u_12, p_u_13, p_u_14):set_text("Penalty cleared.", "Make sure it doesn\'t happen again!")):set_on_close_fn(function() --[[ Line: 161 ]]
                            --[[ Upvalues: (ref 1): p_u_33 ]]
                            p_u_33:on_close()
                        end)
                        p_u_12._chat:set_chat_visible(false)
                    end)
                    p_u_12._player_blob_manager:prompt_product_purchase(p35)
                end;
            end)
            p_u_12._evt:fire_event_to_server(v_u_10.EVT_MatchLeavePenalty_ClientRequestRequiredProductID)
        end;
        v16.behaviour_update = function(p36, p37, p38) --[[ Name: behaviour_update ]] --[[ Line: 173 ]]
            --[[ Upvalues: (ref 1): v_u_22, (copy 2): p_u_15, (copy 3): p_u_12, (ref 4): v_u_8, (ref 5): v_u_23, (ref 6): v_u_1 ]]
            p36:behaviour_update_base(p37, p38)
            v_u_22:update(p37)
            if p_u_15 then
                local v39 = v_u_8:get_match_leave_penalty_end_time((p_u_12._player_blob_manager:get_player_blob())) - p_u_12._player_blob_manager:get_global_time()
                v_u_23.Text = v_u_1:format_sec_time(v39 < 0 and 0 or v39)
            end;
        end;
        v16.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 190 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17:Destroy()
        end;
        v16.layout = function(p40) --[[ Name: layout ]] --[[ Line: 194 ]]
            --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_19, (ref 3): v_u_17, (ref 4): v_u_22 ]]
            p_u_13:uiobj_rescale_to_max_nxy(p40, 0.6, 0.65, v_u_19)
            v_u_17:SetPrimaryPartCFrame(p_u_13:get_cframe({
                ["PositionNXY"] = Vector2.new(0.5, 0.5),
                ["OffsetXYZ"] = p40:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            }))
            v_u_22:layout()
        end;
        v16.set_alpha = function(_, p41) --[[ Name: set_alpha ]] --[[ Line: 204 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_1, (ref 3): v_u_17 ]]
            if v_u_18 ~= p41 then
                v_u_18 = p41
                v_u_1:r_set_alpha(v_u_17, v_u_18)
            end;
        end;
        v16.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 210 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            return v_u_18;
        end;
        v16.set_scale = function(_, p42) --[[ Name: set_scale ]] --[[ Line: 211 ]]
            --[[ Upvalues: (ref 1): v_u_19 ]]
            v_u_19 = p42
        end;
        v16.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 212 ]]
            --[[ Upvalues: (ref 1): v_u_19 ]]
            return v_u_19;
        end;
        v16.get_native_size = function(p43) --[[ Name: get_native_size ]] --[[ Line: 214 ]]
            return p43._native_size;
        end;
        v16.get_size = function(p44) --[[ Name: get_size ]] --[[ Line: 217 ]]
            return p44._size;
        end;
        v16.set_size = function(p45, p46) --[[ Name: set_size ]] --[[ Line: 220 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            p45._size = p46
            v_u_17.PrimaryPart.Size = Vector3.new(p46.X, p46.Y, 0)
        end;
        v16.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 224 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17.PrimaryPart.Position;
        end;
        v16.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 227 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17.PrimaryPart.SurfaceGui;
        end;
        v16:cons()
        return v16;
    end
};
