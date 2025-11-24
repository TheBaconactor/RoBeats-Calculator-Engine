-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:16 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v8 = {}
local v_u_9 = v2:new():push_back_table_list({ "rbxassetid://1338186614", "rbxassetid://1338161352", "rbxassetid://1338161604" })
v8.new = function(_, p_u_10, p_u_11, p_u_12) --[[ Name: new ]] --[[ Line: 21 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_7, (copy 4): v_u_5, (copy 5): v_u_4, (copy 6): v_u_6, (copy 7): v_u_9 ]]
    local v13 = v_u_3:new(p_u_11, p_u_12)
    local v_u_14 = nil
    local v_u_15 = 1
    local v_u_16 = 1
    local v_u_17 = 1
    local v_u_18 = nil
    local v_u_19 = nil
    local v_u_20 = nil
    local v_u_21 = nil
    v13.cons = function(p_u_22) --[[ Name: cons ]] --[[ Line: 34 ]]
        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_1, (ref 3): v_u_7, (ref 4): v_u_19, (ref 5): v_u_18, (ref 6): v_u_20, (copy 7): p_u_10, (ref 8): v_u_5, (ref 9): v_u_4, (copy 10): p_u_11, (ref 11): v_u_6, (ref 12): v_u_21, (copy 13): p_u_12 ]]
        v_u_14 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.TutorialInfoUI:Clone()
        v_u_14.Name = v_u_1:gen_name(v_u_14.Name)
        v_u_14.Parent = v_u_7:get_world_ui_folder()
        p_u_22._native_size = v_u_14.PrimaryPart.Size
        p_u_22._size = p_u_22._native_size
        v_u_19 = v_u_14.MainSurface.SurfaceGui.Frame.Frame.LoadingDisplay
        v_u_18 = v_u_14.MainSurface.SurfaceGui.Frame.Frame.Image
        v_u_20 = p_u_22:add_cycle_element(p_u_10, 1, v_u_5:new(v_u_4:new(p_u_22, v_u_14.PrimaryPart, v_u_14.LeftArrowSurface), p_u_11, function() --[[ Line: 48 ]]
            --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_6, (copy 3): p_u_22 ]]
            p_u_10._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            p_u_22:list_scroll_by(-1)
        end):set_passive_anim())
        v_u_21 = p_u_22:add_cycle_element(p_u_10, 1, v_u_5:new(v_u_4:new(p_u_22, v_u_14.PrimaryPart, v_u_14.RightArrowSurface), p_u_11, function() --[[ Line: 57 ]]
            --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_6, (copy 3): p_u_22 ]]
            p_u_10._sfx_manager:play_sfx(v_u_6.SFX_BUTTONPRESS)
            p_u_22:list_scroll_by(1)
        end):set_passive_anim())
        p_u_22:add_cycle_element(p_u_10, 1, v_u_5:new(v_u_4:new(p_u_22, v_u_14.PrimaryPart, v_u_14.BackButtonSurface), p_u_11, function() --[[ Line: 66 ]]
            --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_6, (ref 3): p_u_12, (copy 4): p_u_22 ]]
            p_u_10._sfx_manager:play_sfx(v_u_6.SFX_MENU_CLOSE)
            p_u_12:remove_menu(p_u_22)
        end))
        p_u_22:add_cycle_element(p_u_10, 1, v_u_5:new(v_u_4:new(p_u_22, v_u_14.PrimaryPart, v_u_14.OkayButtonSurface), p_u_11, function() --[[ Line: 75 ]]
            --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_6, (ref 3): p_u_12, (copy 4): p_u_22 ]]
            p_u_10._sfx_manager:play_sfx(v_u_6.SFX_MENU_CLOSE)
            p_u_12:remove_menu(p_u_22)
        end):set_passive_anim())
        p_u_22:list_scroll_by(0)
        p_u_22:transition_update_visual(0)
        p_u_22:layout()
    end;
    v13.list_scroll_by = function(_, p23) --[[ Name: list_scroll_by ]] --[[ Line: 87 ]]
        --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_1, (ref 3): v_u_9, (ref 4): v_u_20, (ref 5): v_u_21, (ref 6): v_u_18 ]]
        v_u_17 = v_u_1:clamp(v_u_17 + p23, 1, v_u_9:count())
        if v_u_17 == 1 then
            v_u_20:set_visible(false)
            v_u_21:set_visible(true)
        elseif v_u_17 == v_u_9:count() then
            v_u_20:set_visible(true)
            v_u_21:set_visible(false)
        else
            v_u_20:set_visible(true)
            v_u_21:set_visible(true)
        end;
        local v24 = v_u_9:get(v_u_17)
        if v24 ~= nil then
            v_u_18.Image = v24
        end;
    end;
    v13.behaviour_update = function(p25, p26, _) --[[ Name: behaviour_update ]] --[[ Line: 105 ]]
        --[[ Upvalues: (copy 1): p_u_10, (ref 2): v_u_19, (ref 3): v_u_18 ]]
        p25:behaviour_update_base(p26, p_u_10)
        v_u_19.Visible = not v_u_18.IsLoaded
    end;
    v13.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 110 ]]
        --[[ Upvalues: (ref 1): v_u_14 ]]
        v_u_14:Destroy()
    end;
    v13.layout = function(p27) --[[ Name: layout ]] --[[ Line: 114 ]]
        --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_16, (ref 3): v_u_14 ]]
        p27:opt_rescale_to_max_nxy(p_u_11, 0.8, 0.8, v_u_16)
        local v28, v29 = p27:opt_update_cframe_params(p_u_11, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p27:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v28 == true then
            v_u_14:SetPrimaryPartCFrame(v29)
        end;
    end;
    v13.set_alpha = function(_, p30) --[[ Name: set_alpha ]] --[[ Line: 126 ]]
        --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_1, (ref 3): v_u_14 ]]
        if v_u_15 ~= p30 then
            v_u_15 = p30
            v_u_1:r_set_alpha(v_u_14, v_u_15)
        end;
    end;
    v13.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 132 ]]
        --[[ Upvalues: (ref 1): v_u_15 ]]
        return v_u_15;
    end;
    v13.set_scale = function(_, p31) --[[ Name: set_scale ]] --[[ Line: 133 ]]
        --[[ Upvalues: (ref 1): v_u_16 ]]
        v_u_16 = p31
    end;
    v13.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 134 ]]
        --[[ Upvalues: (ref 1): v_u_16 ]]
        return v_u_16;
    end;
    v13.get_native_size = function(p32) --[[ Name: get_native_size ]] --[[ Line: 136 ]]
        return p32._native_size;
    end;
    v13.get_size = function(p33) --[[ Name: get_size ]] --[[ Line: 139 ]]
        return p33._size;
    end;
    v13.set_size = function(p34, p35) --[[ Name: set_size ]] --[[ Line: 142 ]]
        --[[ Upvalues: (ref 1): v_u_14 ]]
        p34._size = p35
        v_u_14.PrimaryPart.Size = Vector3.new(p35.X, p35.Y, 0)
    end;
    v13.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 146 ]]
        --[[ Upvalues: (ref 1): v_u_14 ]]
        return v_u_14.PrimaryPart.Position;
    end;
    v13.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 149 ]]
        --[[ Upvalues: (ref 1): v_u_14 ]]
        return v_u_14.PrimaryPart.SurfaceGui;
    end;
    v13:cons()
    return v13;
end;
return v8;
