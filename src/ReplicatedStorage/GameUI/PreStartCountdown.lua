-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:30 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Shared.ChainCombo)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.EventString)
local v_u_5 = {
    ["CountdownEffect"] = {}
}
v_u_5.CountdownEffect.new = function(_, p_u_6, p_u_7, p_u_8, p_u_9) --[[ Name: new ]] --[[ Line: 15 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_1 ]]
    local v10 = v_u_3:SPUIObjectBase()
    local v_u_11 = 0
    v10.cons = function(p12) --[[ Name: cons ]] --[[ Line: 20 ]]
        --[[ Upvalues: (ref 1): p_u_7 ]]
        p12._native_size = p_u_7.PrimaryPart.Size
        p12._size = p12._native_size
        p12:layout()
    end;
    local v_u_13 = v_u_3:cframe_params_default()
    v10.layout = function(p14) --[[ Name: layout ]] --[[ Line: 27 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_11, (copy 3): p_u_6, (copy 4): v_u_13, (ref 5): p_u_7, (copy 6): p_u_9, (ref 7): v_u_1 ]]
        local l_Y_0 = v_u_2:BezierPt2ForT(0, 1, 0, 0, 1, 1, 1, 0, v_u_11).Y
        local l_Y_1 = v_u_2:BezierPt2ForT(0, 0, 0, 1.25, 1, 1.25, 1, 0, v_u_11).Y
        p_u_6._spui:uiobj_rescale_to_max_nxy(p14, 0.35, 0.35, l_Y_0)
        v_u_13.PositionNXY:set(0.5, 0.5)
        p_u_7:SetPrimaryPartCFrame(p_u_6._spui:get_cframe(v_u_13))
        p_u_9.ImageTransparency = v_u_1:tra(l_Y_1)
    end;
    v10.add_to_parent = function(_, p15, _) --[[ Name: add_to_parent ]] --[[ Line: 52 ]]
        --[[ Upvalues: (ref 1): p_u_7 ]]
        p_u_7.Parent = p15
    end;
    v10.post_update = function(p16, p17, _) --[[ Name: post_update ]] --[[ Line: 56 ]]
        --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_1, (ref 3): v_u_2, (copy 4): p_u_8 ]]
        v_u_11 = v_u_1:clamp(v_u_11 + v_u_2:sec_to_tick(p_u_8 / 1000) * p17, 0, 1)
        p16:layout()
    end;
    v10.should_remove = function(_, _) --[[ Name: should_remove ]] --[[ Line: 61 ]]
        --[[ Upvalues: (ref 1): v_u_11 ]]
        return v_u_11 >= 1;
    end;
    v10.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 65 ]]
        --[[ Upvalues: (ref 1): p_u_7 ]]
        p_u_7:Destroy()
        p_u_7 = nil
    end;
    v10.get_native_size = function(p18) --[[ Name: get_native_size ]] --[[ Line: 72 ]]
        return p18._native_size;
    end;
    v10.get_size = function(p19) --[[ Name: get_size ]] --[[ Line: 76 ]]
        return p19._size;
    end;
    v10.set_size = function(p20, p21) --[[ Name: set_size ]] --[[ Line: 80 ]]
        --[[ Upvalues: (ref 1): p_u_7 ]]
        p20._size = p21
        p_u_7.PrimaryPart.Size = Vector3.new(p21.X, p21.Y, 0)
    end;
    v10:cons()
    return v10;
end;
v_u_5.new = function(_, p_u_22) --[[ Name: new ]] --[[ Line: 89 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_5 ]]
    local v23 = {
        ["cons"] = function(_) end,
        ["teardown"] = function(_) end
    }
    v23.update = function(_, _, _) --[[ Name: update ]] --[[ Line: 98 ]]
        --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_4, (ref 3): v_u_5 ]]
        local v24, v25, v26 = p_u_22:es_gamelocal_get_audiomanager():raise_pre_start_trigger()
        if v24 == true then
            local v27 = game.ReplicatedStorage.WorldUIProto.CountdownNumber:Clone()
            for _, v28 in pairs(v27.MainSurface.SurfaceGui.Frame:GetChildren()) do
                v28.Visible = false
            end;
            local v29
            if v25 == 1 then
                v29 = v27.MainSurface.SurfaceGui.Frame.Image3
                p_u_22._sfx_manager:play_sfx(v_u_4.SFX_COUNTDOWN_READY)
            elseif v25 == 2 then
                v29 = v27.MainSurface.SurfaceGui.Frame.Image2
                p_u_22._sfx_manager:play_sfx(v_u_4.SFX_COUNTDOWN_READY)
            elseif v25 == 3 then
                v29 = v27.MainSurface.SurfaceGui.Frame.Image1
                p_u_22._sfx_manager:play_sfx(v_u_4.SFX_COUNTDOWN_READY)
            else
                v29 = v27.MainSurface.SurfaceGui.Frame.ImageStart
                p_u_22._sfx_manager:play_sfx(v_u_4.SFX_COUNTDOWN_GO)
            end;
            v29.Visible = true
            p_u_22._effects:add_effect(v_u_5.CountdownEffect:new(p_u_22, v27, v26, v29))
        end;
    end;
    v23:cons()
    return v23;
end;
return v_u_5;
