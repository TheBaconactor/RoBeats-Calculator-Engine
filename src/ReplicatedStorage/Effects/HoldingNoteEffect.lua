-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:23 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Effects.EffectSystem)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_5 = require(game.ReplicatedStorage.Shared.PlayerConfig)
local v_u_6 = require(game.ReplicatedStorage.Effects.HoldingNoteEffect_Adorn)
local v_u_21 = {
    ["_new"] = function(_, p_u_7, p_u_8, p_u_9) --[[ Name: _new ]] --[[ Line: 18 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_2, (copy 4): v_u_4 ]]
        local v_u_10 = v_u_1:EffectBase()
        v_u_10.Type = "HoldingNoteEffect"
        v_u_10._effect_obj = nil
        v_u_10._anim_t = 0
        local function f_update_visual(p11) --[[ Name: update_visual ]] --[[ Line: 25 ]]
            --[[ Upvalues: (copy 1): v_u_10, (ref 2): v_u_3 ]]
            v_u_10._effect_obj.Body.Transparency = v_u_3:YForPointOf2PtLine(Vector2.new(0, 0.4), Vector2.new(1, 1), v_u_10._anim_t)
            local v12 = v_u_3:YForPointOf2PtLine(Vector2.new(0, 2), Vector2.new(1, 3.4), v_u_10._anim_t)
            if p11 == true then
                v_u_10._effect_obj.Body.Size = Vector3.new(v12, v12, v12)
            end;
        end;
        v_u_10.cons = function(p13) --[[ Name: cons ]] --[[ Line: 42 ]]
            --[[ Upvalues: (copy 1): p_u_7, (ref 2): v_u_2, (copy 3): p_u_8, (copy 4): p_u_9, (ref 5): v_u_4, (copy 6): f_update_visual ]]
            p13._effect_obj = p_u_7._object_pool:depool(p13.Type)
            if p13._effect_obj == nil then
                p13._effect_obj = game.ReplicatedStorage.ElementProtos.HoldingNoteEffectProto:Clone()
            end;
            p13._effect_obj.Name = v_u_2:gen_name(p13._effect_obj.Name)
            p13._effect_obj.PrimaryPart.Position = p_u_8
            if p_u_9 == v_u_4.NoteResult_Okay then
                p13._effect_obj.PrimaryPart.BrickColor = BrickColor.new(243, 237, 0)
            elseif p_u_9 == v_u_4.NoteResult_Great then
                p13._effect_obj.PrimaryPart.BrickColor = BrickColor.new(0, 255, 0)
            else
                p13._effect_obj.PrimaryPart.BrickColor = BrickColor.new(0, 207, 256)
            end;
            p13._anim_t = 0
            f_update_visual(true)
        end;
        v_u_10.add_to_parent = function(p14, p15, _) --[[ Name: add_to_parent ]] --[[ Line: 63 ]]
            p14._effect_obj.Parent = p15
        end;
        local v_u_16 = 0
        v_u_10.update = function(p17, p18, _) --[[ Name: update ]] --[[ Line: 68 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_3, (ref 3): v_u_16, (copy 4): f_update_visual ]]
            v_u_2:profilebegin("HoldingNoteEffect")
            p17._anim_t = p17._anim_t + v_u_3:SecondsToTick(0.35) * p18
            v_u_16 = v_u_16
            if v_u_16 > 4 then
                f_update_visual(true)
                v_u_16 = v_u_16 - 4
            else
                f_update_visual(false)
            end;
            v_u_2:profileend()
        end;
        v_u_10.should_remove = function(p19, _) --[[ Name: should_remove ]] --[[ Line: 82 ]]
            return p19._anim_t >= 1;
        end;
        v_u_10.do_remove = function(p20, _) --[[ Name: do_remove ]] --[[ Line: 85 ]]
            --[[ Upvalues: (copy 1): p_u_7 ]]
            p_u_7._object_pool:repool(p20.Type, p20._effect_obj)
            p20._effect_obj = nil
        end;
        v_u_10:cons()
        return v_u_10;
    end
}
v_u_21.new = function(_, p22, p23, p24) --[[ Name: new ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_6, (copy 3): v_u_21 ]]
    if v_u_5.GameEffectsUseAdorns == true then
        return v_u_6:new(p22, p23, p24);
    else
        return v_u_21:_new(p22, p23, p24);
    end;
end;
return v_u_21;
