-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:44 PM
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
local v_u_7 = require(game.ReplicatedStorage.Lobby.UI.SPUITextInput)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.DebugConfig)
return {
    ["new"] = function(_, p_u_8, p_u_9, p_u_10, p_u_11, p_u_12, p_u_13) --[[ Name: new ]] --[[ Line: 18 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_6, (copy 4): v_u_4, (copy 5): v_u_3, (copy 6): v_u_5, (copy 7): v_u_7 ]]
        local v14 = v_u_2:new(p_u_9, p_u_10)
        local v_u_15 = nil
        local v_u_16 = nil
        local v_u_17 = nil
        v14.cons = function(p_u_18) --[[ Name: cons ]] --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_1, (ref 3): v_u_6, (copy 4): p_u_11, (copy 5): p_u_12, (copy 6): p_u_8, (ref 7): v_u_4, (ref 8): v_u_3, (copy 9): p_u_9, (copy 10): p_u_10, (ref 11): v_u_5, (ref 12): v_u_16, (ref 13): v_u_17, (copy 14): p_u_13, (ref 15): v_u_7 ]]
            v_u_15 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Util.TextInputUI:Clone()
            v_u_15.Name = v_u_1:gen_name(v_u_15.Name)
            v_u_15.Parent = v_u_6:get_world_ui_folder()
            p_u_18._native_size = v_u_15.PrimaryPart.Size
            p_u_18._size = p_u_18._native_size
            local l_Frame_0 = v_u_15.MainSurface.SurfaceGui.Frame
            l_Frame_0.TextSection.TitleText.Text = p_u_11
            l_Frame_0.TextSection.SubText.Text = p_u_12
            p_u_18:add_cycle_element(p_u_8, 1, v_u_4:new(v_u_3:new(p_u_18, v_u_15.PrimaryPart, v_u_15.BackButtonSurface), p_u_9, function() --[[ Line: 40 ]]
                --[[ Upvalues: (ref 1): p_u_10, (copy 2): p_u_18, (ref 3): p_u_8, (ref 4): v_u_5 ]]
                p_u_10:remove_menu(p_u_18)
                p_u_8._sfx_manager:play_sfx(v_u_5.SFX_MENU_CLOSE)
            end))
            v_u_16 = p_u_18:add_cycle_element(p_u_8, 1, v_u_4:new(v_u_3:new(p_u_18, v_u_15.PrimaryPart, v_u_15.OkayButtonSurface), p_u_9, function() --[[ Line: 49 ]]
                --[[ Upvalues: (ref 1): p_u_8, (ref 2): v_u_5, (ref 3): v_u_17, (ref 4): v_u_1, (ref 5): p_u_13, (ref 6): p_u_10, (copy 7): p_u_18 ]]
                p_u_8._sfx_manager:play_sfx(v_u_5.SFX_MENU_OPEN)
                if v_u_17:get_enforce_numeric() then
                    local v19 = tonumber(v_u_17:get_current_text())
                    local v20 = v19 == nil and 0 or v19
                    if v_u_1:input_max_number() < v20 then
                        v20 = v_u_1:input_max_number()
                    end;
                    if v20 < -v_u_1:input_max_number() then
                        v20 = -v_u_1:input_max_number()
                    end;
                    p_u_13(v20)
                else
                    p_u_13(v_u_17:get_current_text())
                end;
                p_u_10:remove_menu(p_u_18)
            end):set_passive_anim())
            v_u_17 = v_u_7:new(p_u_8, l_Frame_0.TextSection.InputBarFrame.TextLabel, nil, p_u_18, p_u_9):set_send_behaviour_enabled(false)
            p_u_18:transition_update_visual(0)
            p_u_18:layout()
        end;
        v14.set_text = function(p21, p22) --[[ Name: set_text ]] --[[ Line: 83 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17:set_text(p22)
            return p21;
        end;
        v14.set_empty_message = function(p23, p24) --[[ Name: set_empty_message ]] --[[ Line: 88 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17:set_empty_message(p24)
            return p23;
        end;
        v14.set_max_length = function(p25, p26) --[[ Name: set_max_length ]] --[[ Line: 93 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17:set_max_length(p26)
            return p25;
        end;
        v14.force_int_in_range = function(p27, p_u_28, p_u_29) --[[ Name: force_int_in_range ]] --[[ Line: 98 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_1 ]]
            v_u_17:enforce_numeric(true, function(p30) --[[ Line: 99 ]]
                --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_28, (copy 3): p_u_29 ]]
                return v_u_1:clamp(math.floor(p30), p_u_28, p_u_29);
            end):enforce_numeric_integer(true)
            return p27;
        end;
        v14.behaviour_update = function(p31, p32, _) --[[ Name: behaviour_update ]] --[[ Line: 105 ]]
            --[[ Upvalues: (copy 1): p_u_8, (ref 2): v_u_17 ]]
            p31:behaviour_update_base(p32, p_u_8)
            v_u_17:update(p32)
        end;
        v14.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 110 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_17 ]]
            v_u_15:Destroy()
            v_u_17:cleanup()
        end;
        v14.layout = function(p33) --[[ Name: layout ]] --[[ Line: 115 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_15 ]]
            p33:opt_rescale_to_max_nxy(p_u_9, 0.88, 0.8, p33:get_scale())
            local v34, v35 = p33:opt_update_cframe_params(p_u_9, {
                ["PositionNXY"] = Vector2.new(0.5, 0.45),
                ["OffsetXYZ"] = p33:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            })
            if v34 == true then
                v_u_15:SetPrimaryPartCFrame(v35)
            end;
        end;
        local v_u_36 = 1
        local v_u_37 = 1
        v14.set_alpha = function(_, p38) --[[ Name: set_alpha ]] --[[ Line: 129 ]]
            --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_1, (ref 3): v_u_15 ]]
            if v_u_36 ~= p38 then
                v_u_36 = p38
                v_u_1:r_set_alpha(v_u_15, v_u_36)
            end;
        end;
        v14.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 135 ]]
            --[[ Upvalues: (ref 1): v_u_36 ]]
            return v_u_36;
        end;
        v14.set_scale = function(_, p39) --[[ Name: set_scale ]] --[[ Line: 136 ]]
            --[[ Upvalues: (ref 1): v_u_37 ]]
            v_u_37 = p39
        end;
        v14.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 137 ]]
            --[[ Upvalues: (ref 1): v_u_37 ]]
            return v_u_37;
        end;
        v14.get_native_size = function(p40) --[[ Name: get_native_size ]] --[[ Line: 139 ]]
            return p40._native_size;
        end;
        v14.get_size = function(p41) --[[ Name: get_size ]] --[[ Line: 142 ]]
            return p41._size;
        end;
        v14.set_size = function(p42, p43) --[[ Name: set_size ]] --[[ Line: 145 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            p42._size = p43
            v_u_15.PrimaryPart.Size = Vector3.new(p43.X, p43.Y, 0)
        end;
        v14.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 149 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            return v_u_15.PrimaryPart.Position;
        end;
        v14.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 150 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            return v_u_15.PrimaryPart.SurfaceGui;
        end;
        v14.set_showing = function(_, p44) --[[ Name: set_showing ]] --[[ Line: 151 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_6 ]]
            if p44 then
                v_u_15.Parent = v_u_6:get_world_ui_folder()
            else
                v_u_15.Parent = nil
            end;
        end;
        v14:cons()
        return v14;
    end
};
