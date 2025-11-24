-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:47 PM
-- Time elapsed: 11 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_6 = require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Lobby.UI.EquipUI.CharacterDisplaySection)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.Dependency):require_client(function() end)
return {
    ["new"] = function(_, p_u_9, p_u_10, p_u_11) --[[ Name: new ]] --[[ Line: 25 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_7, (copy 5): v_u_5, (copy 6): v_u_4, (copy 7): v_u_8, (copy 8): v_u_6 ]]
        local v_u_12 = v_u_3:new(p_u_10, p_u_11)
        local v_u_13 = nil
        local v_u_14 = 1
        local v_u_15 = 1
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = nil
        local v_u_19 = nil
        local v_u_20 = nil
        v_u_12.get_image = function(_) --[[ Name: get_image ]] --[[ Line: 37 ]]
            --[[ Upvalues: (ref 1): v_u_19 ]]
            return v_u_19;
        end;
        v_u_12.get_image_overlay = function(_) --[[ Name: get_image_overlay ]] --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20;
        end;
        local v_u_21 = v_u_2:new()
        v_u_12.get_action_buttons = function(_) --[[ Name: get_action_buttons ]] --[[ Line: 41 ]]
            --[[ Upvalues: (copy 1): v_u_21 ]]
            return v_u_21;
        end;
        local function f_cons() --[[ Name: cons ]] --[[ Line: 43 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_1, (ref 3): v_u_7, (copy 4): v_u_12, (ref 5): v_u_16, (ref 6): v_u_17, (ref 7): v_u_18, (copy 8): p_u_9, (ref 9): v_u_5, (ref 10): v_u_4, (copy 11): p_u_10, (ref 12): v_u_8, (copy 13): p_u_11, (ref 14): v_u_19, (ref 15): v_u_20, (ref 16): v_u_2, (copy 17): v_u_21 ]]
            v_u_13 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Util.PreviewImageUI:Clone()
            v_u_13.Name = v_u_1:gen_name(v_u_13.Name)
            v_u_13.Parent = v_u_7:get_world_ui_folder()
            v_u_12._native_size = v_u_13.PrimaryPart.Size
            v_u_12._size = v_u_12._native_size
            v_u_16 = v_u_13.MainSurface.SurfaceGui.Frame
            v_u_17 = v_u_16.TextSection.NameDisplay
            v_u_18 = v_u_16.TextSection.DescriptionDisplay
            v_u_17.Text = ""
            v_u_18.Text = ""
            v_u_12:add_cycle_element(p_u_9, 1, v_u_5:new(v_u_4:new(v_u_12, v_u_13.PrimaryPart, v_u_13.BackButtonSurface), p_u_10, function() --[[ Line: 59 ]]
                --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_8, (ref 3): p_u_11, (ref 4): v_u_12 ]]
                p_u_9._sfx_manager:play_sfx(v_u_8.SFX_MENU_CLOSE)
                p_u_11:remove_menu(v_u_12)
            end))
            v_u_19 = v_u_16.ImageSection.Icon
            v_u_19.Image = v_u_1:transparent_assetid()
            v_u_20 = v_u_16.ImageSection.IconOverlay
            v_u_20.Image = v_u_1:transparent_assetid()
            v_u_20.Visible = false
            for _, v22 in v_u_2:new({
                v_u_13.Buttons.Button1,
                v_u_13.Buttons.Button2,
                v_u_13.Buttons.Button3,
                v_u_13.Buttons.Button4,
                v_u_13.Buttons.Button5
            }):key_itr() do
                local v_u_23 = nil
                v_u_23 = v_u_12:add_cycle_element(p_u_9, 1, v_u_5:new(v_u_4:new(v_u_12, v_u_13.PrimaryPart, v22), p_u_10, function() --[[ Line: 76 ]]
                    --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_8, (ref 3): v_u_23 ]]
                    p_u_9._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
                    if v_u_23:get_bound_data() ~= nil then
                        v_u_23:get_bound_data()()
                    end;
                end))
                v_u_23:set_visible(false)
                v_u_21:push_back(v_u_23)
            end;
        end;
        v_u_12.set_text = function(p24, p25, p_u_26, p27) --[[ Name: set_text ]] --[[ Line: 88 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_18, (ref 3): v_u_6 ]]
            v_u_17.Text = p25
            if p27 == true then
                local v28, v29 = pcall(function() --[[ Line: 91 ]]
                    --[[ Upvalues: (ref 1): v_u_18, (copy 2): p_u_26 ]]
                    v_u_18.RichText = true
                    v_u_18.Text = p_u_26
                end)
                if v28 ~= true then
                    v_u_6:puts("PreviewImageUI:set_text() failed to set rich text: " .. v29)
                    v_u_18.RichText = false
                    v_u_18.Text = p_u_26
                    return p24;
                end;
            else
                v_u_18.RichText = false
                v_u_18.Text = p_u_26
            end;
            return p24;
        end;
        v_u_12.layout = function(p30) --[[ Name: layout ]] --[[ Line: 108 ]]
            --[[ Upvalues: (copy 1): p_u_10, (ref 2): v_u_15, (ref 3): v_u_13 ]]
            p30:opt_rescale_to_max_nxy(p_u_10, 0.8, 0.8, v_u_15)
            local v31, v32 = p30:opt_update_cframe_params(p_u_10, {
                ["PositionNXY"] = Vector2.new(0.5, 0.5),
                ["OffsetXYZ"] = p30:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            })
            if v31 == true then
                v_u_13:SetPrimaryPartCFrame(v32)
            end;
        end;
        v_u_12.visual_update = function(p33, p34, p35) --[[ Name: visual_update ]] --[[ Line: 120 ]]
            p33:visual_update_base(p34, p35)
        end;
        v_u_12.behaviour_update = function(p36, p37) --[[ Name: behaviour_update ]] --[[ Line: 124 ]]
            --[[ Upvalues: (copy 1): p_u_9 ]]
            p36:behaviour_update_base(p37, p_u_9)
        end;
        local v_u_38 = nil
        v_u_12.set_fn_on_remove = function(p39, p40) --[[ Name: set_fn_on_remove ]] --[[ Line: 129 ]]
            --[[ Upvalues: (ref 1): v_u_38 ]]
            v_u_38 = p40
            return p39;
        end;
        v_u_12.do_remove = function(_) --[[ Name: do_remove ]] --[[ Line: 134 ]]
            --[[ Upvalues: (ref 1): v_u_38, (ref 2): v_u_13 ]]
            if v_u_38 then
                v_u_38()
            end;
            v_u_13:Destroy()
        end;
        v_u_12.set_alpha = function(_, p41) --[[ Name: set_alpha ]] --[[ Line: 139 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_1, (ref 3): v_u_13 ]]
            if v_u_14 ~= p41 then
                v_u_14 = p41
                v_u_1:r_set_alpha(v_u_13, v_u_14)
            end;
        end;
        v_u_12.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 145 ]]
            --[[ Upvalues: (ref 1): v_u_14 ]]
            return v_u_14;
        end;
        v_u_12.set_scale = function(_, p42) --[[ Name: set_scale ]] --[[ Line: 146 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            v_u_15 = p42
        end;
        v_u_12.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 147 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            return v_u_15;
        end;
        v_u_12.get_native_size = function(p43) --[[ Name: get_native_size ]] --[[ Line: 149 ]]
            return p43._native_size;
        end;
        v_u_12.get_size = function(p44) --[[ Name: get_size ]] --[[ Line: 152 ]]
            return p44._size;
        end;
        v_u_12.set_size = function(p45, p46) --[[ Name: set_size ]] --[[ Line: 155 ]]
            --[[ Upvalues: (ref 1): v_u_13 ]]
            p45._size = p46
            v_u_13.PrimaryPart.Size = Vector3.new(p46.X, p46.Y, 0)
        end;
        v_u_12.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 159 ]]
            --[[ Upvalues: (ref 1): v_u_13 ]]
            return v_u_13.PrimaryPart.Position;
        end;
        v_u_12.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 162 ]]
            --[[ Upvalues: (ref 1): v_u_13 ]]
            return v_u_13.PrimaryPart.SurfaceGui;
        end;
        v_u_12.set_showing = function(_, p47) --[[ Name: set_showing ]] --[[ Line: 165 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_7 ]]
            if p47 then
                v_u_13.Parent = v_u_7:get_world_ui_folder()
            else
                v_u_13.Parent = nil
            end;
        end;
        f_cons()
        return v_u_12;
    end
};
