-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:45 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_9 = require(game.ReplicatedStorage.Avatar.ElementalColor)
return {
    ["new"] = function(_, p_u_10, p_u_11, p_u_12, p_u_13, p_u_14, p_u_15) --[[ Name: new ]] --[[ Line: 17 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_8, (copy 5): v_u_6, (copy 6): v_u_5, (copy 7): v_u_7, (copy 8): v_u_3, (copy 9): v_u_9 ]]
        local v_u_16 = v_u_4:new(p_u_11, p_u_12)
        local v_u_17 = nil
        local v_u_18 = nil
        local v_u_19 = v_u_2:new()
        local function f_cons() --[[ Name: cons ]] --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_1, (ref 3): v_u_8, (copy 4): v_u_16, (copy 5): p_u_13, (copy 6): p_u_14, (copy 7): p_u_10, (ref 8): v_u_6, (ref 9): v_u_5, (copy 10): p_u_11, (copy 11): p_u_12, (ref 12): v_u_7, (ref 13): v_u_3, (ref 14): v_u_9, (copy 15): p_u_15, (copy 16): v_u_19, (ref 17): v_u_18 ]]
            v_u_17 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.ColorSelectUI:Clone()
            v_u_17.Name = v_u_1:gen_name(v_u_17.Name)
            v_u_17.Parent = v_u_8:get_world_ui_folder()
            v_u_16._native_size = v_u_17.PrimaryPart.Size
            v_u_16._size = v_u_16._native_size
            local l_Frame_0 = v_u_17.MainSurface.SurfaceGui.Frame
            l_Frame_0.TextSection.TitleText.Text = p_u_13
            l_Frame_0.TextSection.SubText.Text = p_u_14
            v_u_16:add_cycle_element(p_u_10, 1, v_u_6:new(v_u_5:new(v_u_16, v_u_17.PrimaryPart, v_u_17.BackButtonSurface), p_u_11, function() --[[ Line: 40 ]]
                --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_16, (ref 3): p_u_10, (ref 4): v_u_7 ]]
                p_u_12:remove_menu(v_u_16)
                p_u_10._sfx_manager:play_sfx(v_u_7.SFX_MENU_CLOSE)
            end))
            local v20 = v_u_3:new():push_back_table_list({
                v_u_17.ColorButton1,
                v_u_17.ColorButton2,
                v_u_17.ColorButton3,
                v_u_17.ColorButton4,
                v_u_17.ColorButton5
            })
            for v21 = 1, v20:count() do
                local v22 = v20:get(v21)
                if v21 <= v_u_9:colors_list():count() then
                    local v_u_23 = v_u_9:colors_list():get(v21)
                    v22.SurfaceGui.Frame.ColorIcon.Image = v_u_9:color_to_iconimage(v_u_23)
                    v22.SurfaceGui.Frame.ColorText.Image = v_u_9:color_to_textimage(v_u_23)
                    v_u_19:add(v_u_23, (v_u_16:add_cycle_element(p_u_10, 1, v_u_6:new(v_u_5:new(v_u_16, v_u_17.PrimaryPart, v22), p_u_11, function() --[[ Line: 62 ]]
                        --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_16, (ref 3): p_u_10, (ref 4): v_u_7, (ref 5): p_u_15, (copy 6): v_u_23 ]]
                        p_u_12:remove_menu(v_u_16)
                        p_u_10._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                        p_u_15(v_u_23)
                    end))))
                else
                    v22.Parent = nil
                end;
            end;
            v_u_18 = v_u_16:add_cycle_element(p_u_10, 1, v_u_6:new(v_u_5:new(v_u_16, v_u_17.PrimaryPart, v_u_17.NoneButton), p_u_11, function() --[[ Line: 77 ]]
                --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_16, (ref 3): p_u_10, (ref 4): v_u_7, (ref 5): p_u_15, (ref 6): v_u_9 ]]
                p_u_12:remove_menu(v_u_16)
                p_u_10._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                p_u_15(v_u_9:color_none())
            end))
            v_u_18:set_visible(false)
            v_u_16:transition_update_visual(0)
            v_u_16:layout()
        end;
        v_u_16.set_none_selectable = function(p24) --[[ Name: set_none_selectable ]] --[[ Line: 89 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            v_u_18:set_visible(true)
            return p24;
        end;
        v_u_16.set_color_button_visible = function(p25, p26, p27) --[[ Name: set_color_button_visible ]] --[[ Line: 94 ]]
            --[[ Upvalues: (copy 1): v_u_19 ]]
            if v_u_19:contains(p26) then
                v_u_19:get(p26):set_visible(p27)
            end;
            return p25;
        end;
        v_u_16.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 101 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17:Destroy()
        end;
        v_u_16.layout = function(p28) --[[ Name: layout ]] --[[ Line: 105 ]]
            --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_17 ]]
            p28:opt_rescale_to_max_nxy(p_u_11, 0.88, 0.8, p28:get_scale())
            local v29, v30 = p28:opt_update_cframe_params(p_u_11, {
                ["PositionNXY"] = Vector2.new(0.5, 0.5),
                ["OffsetXYZ"] = p28:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            })
            if v29 == true then
                v_u_17:SetPrimaryPartCFrame(v30)
            end;
        end;
        local v_u_31 = 1
        local v_u_32 = 1
        v_u_16.set_alpha = function(_, p33) --[[ Name: set_alpha ]] --[[ Line: 119 ]]
            --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_1, (ref 3): v_u_17 ]]
            if v_u_31 ~= p33 then
                v_u_31 = p33
                v_u_1:r_set_alpha(v_u_17, v_u_31)
            end;
        end;
        v_u_16.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 125 ]]
            --[[ Upvalues: (ref 1): v_u_31 ]]
            return v_u_31;
        end;
        v_u_16.set_scale = function(_, p34) --[[ Name: set_scale ]] --[[ Line: 126 ]]
            --[[ Upvalues: (ref 1): v_u_32 ]]
            v_u_32 = p34
        end;
        v_u_16.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 127 ]]
            --[[ Upvalues: (ref 1): v_u_32 ]]
            return v_u_32;
        end;
        v_u_16.get_native_size = function(p35) --[[ Name: get_native_size ]] --[[ Line: 129 ]]
            return p35._native_size;
        end;
        v_u_16.get_size = function(p36) --[[ Name: get_size ]] --[[ Line: 132 ]]
            return p36._size;
        end;
        v_u_16.set_size = function(p37, p38) --[[ Name: set_size ]] --[[ Line: 135 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            p37._size = p38
            v_u_17.PrimaryPart.Size = Vector3.new(p38.X, p38.Y, 0)
        end;
        v_u_16.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 139 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17.PrimaryPart.Position;
        end;
        v_u_16.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 140 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17.PrimaryPart.SurfaceGui;
        end;
        v_u_16.set_showing = function(_, p39) --[[ Name: set_showing ]] --[[ Line: 141 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_8 ]]
            if p39 then
                v_u_17.Parent = v_u_8:get_world_ui_folder()
            else
                v_u_17.Parent = nil
            end;
        end;
        f_cons()
        return v_u_16;
    end
};
