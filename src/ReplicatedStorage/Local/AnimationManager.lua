-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:24 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_3 = {
    ["ANIM_TANTRUM"] = 1,
    ["ANIM_DIZZYFALL"] = 2,
    ["ANIM_SIGH"] = 3,
    ["ANIM_SWAY"] = 4,
    ["ANIM_SPINPOSE"] = 5,
    ["ANIM_FOURSTEPSWAY"] = 6,
    ["ANIM_WAVE"] = 7,
    ["ANIM_OLDSCHOOLSHUFFLE"] = 8,
    ["ANIM_HIPHOPSWAY"] = 9,
    ["ANIM_IDLE"] = 10,
    ["ANIM_BREAKDANCE"] = 11,
    ["ANIM_BREAKDANCESPIN"] = 12,
    ["ANIM_DANCEROYALE"] = 13,
    ["ANIM_STARMACHINE_BOUNCE"] = 103,
    ["ANIM_MARIE_TALK"] = 214,
    ["ANIM_MATTIE_TALK"] = 215,
    ["ANIM_MARIE_IDLE"] = 216,
    ["ANIM_MATTIE_IDLE"] = 217,
    ["ANIM_MARIE_CHEER"] = 218,
    ["ANIM_MATTIE_CHEER"] = 219,
    ["ANIM_LISA_IDLE"] = 220,
    ["ANIM_DJ_IDLE"] = 221,
    ["ANIM_MARKETPLACE_IDLE"] = 222,
    ["ANIM_TEAM_IDLE"] = 223,
    ["ANIM_DANCE1"] = 319,
    ["ANIM_ROBLOX_WAVE"] = 420,
    ["ANIM_ROBLOX_CHEER"] = 421,
    ["ANIM_ROBLOX_LAUGH"] = 422
}
v_u_3.ANIM_WAVE = 318
v_u_3.new = function(_) --[[ Name: new ]] --[[ Line: 46 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_2 ]]
    local v4 = {}
    local v_u_5 = v_u_1:new()
    local s_KeyframeSequenceProvider_0 = game:GetService("KeyframeSequenceProvider")
    local function _(p6) --[[ Name: make_animation_from_keyframe_sequence ]] --[[ Line: 52 ]]
        --[[ Upvalues: (copy 1): s_KeyframeSequenceProvider_0 ]]
        local l_Animation_0 = Instance.new("Animation")
        l_Animation_0.AnimationId = s_KeyframeSequenceProvider_0:RegisterKeyframeSequence(p6)
        return l_Animation_0;
    end;
    local function _(p7) --[[ Name: make_animation_from_assetid ]] --[[ Line: 58 ]]
        local l_Animation_1 = Instance.new("Animation")
        l_Animation_1.AnimationId = p7
        return l_Animation_1;
    end;
    v4.cons = function(_) --[[ Name: cons ]] --[[ Line: 64 ]]
        --[[ Upvalues: (copy 1): v_u_5, (ref 2): v_u_3 ]]
        local v8 = v_u_5
        local l_ANIM_TANTRUM_0 = v_u_3.ANIM_TANTRUM
        local l_Animation_2 = Instance.new("Animation")
        l_Animation_2.AnimationId = "rbxassetid://713285606"
        v8:add(l_ANIM_TANTRUM_0, l_Animation_2)
        local v9 = v_u_5
        local l_ANIM_DIZZYFALL_0 = v_u_3.ANIM_DIZZYFALL
        local l_Animation_3 = Instance.new("Animation")
        l_Animation_3.AnimationId = "rbxassetid://713231237"
        v9:add(l_ANIM_DIZZYFALL_0, l_Animation_3)
        local v10 = v_u_5
        local l_ANIM_SIGH_0 = v_u_3.ANIM_SIGH
        local l_Animation_4 = Instance.new("Animation")
        l_Animation_4.AnimationId = "rbxassetid://710037303"
        v10:add(l_ANIM_SIGH_0, l_Animation_4)
        local v11 = v_u_5
        local l_ANIM_SWAY_0 = v_u_3.ANIM_SWAY
        local l_Animation_5 = Instance.new("Animation")
        l_Animation_5.AnimationId = "rbxassetid://705870851"
        v11:add(l_ANIM_SWAY_0, l_Animation_5)
        local v12 = v_u_5
        local l_ANIM_SPINPOSE_0 = v_u_3.ANIM_SPINPOSE
        local l_Animation_6 = Instance.new("Animation")
        l_Animation_6.AnimationId = "rbxassetid://711635385"
        v12:add(l_ANIM_SPINPOSE_0, l_Animation_6)
        local v13 = v_u_5
        local l_ANIM_FOURSTEPSWAY_0 = v_u_3.ANIM_FOURSTEPSWAY
        local l_Animation_7 = Instance.new("Animation")
        l_Animation_7.AnimationId = "rbxassetid://716156761"
        v13:add(l_ANIM_FOURSTEPSWAY_0, l_Animation_7)
        local v14 = v_u_5
        local l_ANIM_WAVE_0 = v_u_3.ANIM_WAVE
        local l_Animation_8 = Instance.new("Animation")
        l_Animation_8.AnimationId = "rbxassetid://716494029"
        v14:add(l_ANIM_WAVE_0, l_Animation_8)
        local v15 = v_u_5
        local l_ANIM_OLDSCHOOLSHUFFLE_0 = v_u_3.ANIM_OLDSCHOOLSHUFFLE
        local l_Animation_9 = Instance.new("Animation")
        l_Animation_9.AnimationId = "rbxassetid://718420920"
        v15:add(l_ANIM_OLDSCHOOLSHUFFLE_0, l_Animation_9)
        local v16 = v_u_5
        local l_ANIM_HIPHOPSWAY_0 = v_u_3.ANIM_HIPHOPSWAY
        local l_Animation_10 = Instance.new("Animation")
        l_Animation_10.AnimationId = "rbxassetid://717481497"
        v16:add(l_ANIM_HIPHOPSWAY_0, l_Animation_10)
        local v17 = v_u_5
        local l_ANIM_IDLE_0 = v_u_3.ANIM_IDLE
        local l_Animation_11 = Instance.new("Animation")
        l_Animation_11.AnimationId = "rbxassetid://721463188"
        v17:add(l_ANIM_IDLE_0, l_Animation_11)
        local v18 = v_u_5
        local l_ANIM_BREAKDANCE_0 = v_u_3.ANIM_BREAKDANCE
        local l_Animation_12 = Instance.new("Animation")
        l_Animation_12.AnimationId = "rbxassetid://731452379"
        v18:add(l_ANIM_BREAKDANCE_0, l_Animation_12)
        local v19 = v_u_5
        local l_ANIM_BREAKDANCESPIN_0 = v_u_3.ANIM_BREAKDANCESPIN
        local l_Animation_13 = Instance.new("Animation")
        l_Animation_13.AnimationId = "rbxassetid://732270556"
        v19:add(l_ANIM_BREAKDANCESPIN_0, l_Animation_13)
        local v20 = v_u_5
        local l_ANIM_DANCEROYALE_0 = v_u_3.ANIM_DANCEROYALE
        local l_Animation_14 = Instance.new("Animation")
        l_Animation_14.AnimationId = "rbxassetid://1691195191"
        v20:add(l_ANIM_DANCEROYALE_0, l_Animation_14)
        local v21 = v_u_5
        local l_ANIM_STARMACHINE_BOUNCE_0 = v_u_3.ANIM_STARMACHINE_BOUNCE
        local l_Animation_15 = Instance.new("Animation")
        l_Animation_15.AnimationId = "rbxassetid://908312878"
        v21:add(l_ANIM_STARMACHINE_BOUNCE_0, l_Animation_15)
        local v22 = v_u_5
        local l_ANIM_MATTIE_IDLE_0 = v_u_3.ANIM_MATTIE_IDLE
        local l_Animation_16 = Instance.new("Animation")
        l_Animation_16.AnimationId = "rbxassetid://882859781"
        v22:add(l_ANIM_MATTIE_IDLE_0, l_Animation_16)
        local v23 = v_u_5
        local l_ANIM_MARIE_IDLE_0 = v_u_3.ANIM_MARIE_IDLE
        local l_Animation_17 = Instance.new("Animation")
        l_Animation_17.AnimationId = "rbxassetid://884198066"
        v23:add(l_ANIM_MARIE_IDLE_0, l_Animation_17)
        local v24 = v_u_5
        local l_ANIM_MATTIE_TALK_0 = v_u_3.ANIM_MATTIE_TALK
        local l_Animation_18 = Instance.new("Animation")
        l_Animation_18.AnimationId = "rbxassetid://882789064"
        v24:add(l_ANIM_MATTIE_TALK_0, l_Animation_18)
        local v25 = v_u_5
        local l_ANIM_MARIE_TALK_0 = v_u_3.ANIM_MARIE_TALK
        local l_Animation_19 = Instance.new("Animation")
        l_Animation_19.AnimationId = "rbxassetid://884233580"
        v25:add(l_ANIM_MARIE_TALK_0, l_Animation_19)
        local v26 = v_u_5
        local l_ANIM_LISA_IDLE_0 = v_u_3.ANIM_LISA_IDLE
        local l_Animation_20 = Instance.new("Animation")
        l_Animation_20.AnimationId = "rbxassetid://2081948416"
        v26:add(l_ANIM_LISA_IDLE_0, l_Animation_20)
        local v27 = v_u_5
        local l_ANIM_DANCE1_0 = v_u_3.ANIM_DANCE1
        local l_Animation_21 = Instance.new("Animation")
        l_Animation_21.AnimationId = "rbxassetid://507771019"
        v27:add(l_ANIM_DANCE1_0, l_Animation_21)
        local v28 = v_u_5
        local l_ANIM_ROBLOX_WAVE_0 = v_u_3.ANIM_ROBLOX_WAVE
        local l_Animation_22 = Instance.new("Animation")
        l_Animation_22.AnimationId = "rbxassetid://507770239"
        v28:add(l_ANIM_ROBLOX_WAVE_0, l_Animation_22)
        local v29 = v_u_5
        local l_ANIM_ROBLOX_CHEER_0 = v_u_3.ANIM_ROBLOX_CHEER
        local l_Animation_23 = Instance.new("Animation")
        l_Animation_23.AnimationId = "rbxassetid://507770677"
        v29:add(l_ANIM_ROBLOX_CHEER_0, l_Animation_23)
        local v30 = v_u_5
        local l_ANIM_ROBLOX_LAUGH_0 = v_u_3.ANIM_ROBLOX_LAUGH
        local l_Animation_24 = Instance.new("Animation")
        l_Animation_24.AnimationId = "rbxassetid://507770818"
        v30:add(l_ANIM_ROBLOX_LAUGH_0, l_Animation_24)
        local v31 = v_u_5
        local l_ANIM_MARIE_CHEER_0 = v_u_3.ANIM_MARIE_CHEER
        local l_Animation_25 = Instance.new("Animation")
        l_Animation_25.AnimationId = "rbxassetid://923142105"
        v31:add(l_ANIM_MARIE_CHEER_0, l_Animation_25)
        local v32 = v_u_5
        local l_ANIM_MATTIE_CHEER_0 = v_u_3.ANIM_MATTIE_CHEER
        local l_Animation_26 = Instance.new("Animation")
        l_Animation_26.AnimationId = "rbxassetid://882846241"
        v32:add(l_ANIM_MATTIE_CHEER_0, l_Animation_26)
        local v33 = v_u_5
        local l_ANIM_DJ_IDLE_0 = v_u_3.ANIM_DJ_IDLE
        local l_Animation_27 = Instance.new("Animation")
        l_Animation_27.AnimationId = "rbxassetid://3050029382"
        v33:add(l_ANIM_DJ_IDLE_0, l_Animation_27)
        local v34 = v_u_5
        local l_ANIM_MARKETPLACE_IDLE_0 = v_u_3.ANIM_MARKETPLACE_IDLE
        local l_Animation_28 = Instance.new("Animation")
        l_Animation_28.AnimationId = "rbxassetid://4675660791"
        v34:add(l_ANIM_MARKETPLACE_IDLE_0, l_Animation_28)
        local v35 = v_u_5
        local l_ANIM_TEAM_IDLE_0 = v_u_3.ANIM_TEAM_IDLE
        local l_Animation_29 = Instance.new("Animation")
        l_Animation_29.AnimationId = "rbxassetid://7000241368"
        v35:add(l_ANIM_TEAM_IDLE_0, l_Animation_29)
    end;
    v4.get_anim = function(_, p36) --[[ Name: get_anim ]] --[[ Line: 106 ]]
        --[[ Upvalues: (copy 1): v_u_5, (ref 2): v_u_2 ]]
        if v_u_5:contains(p36) == false then
            v_u_2:errf("AnimationManager does not contain animation(%s)", p36)
        end;
        return v_u_5:get(p36);
    end;
    v4:cons()
    return v4;
end;
return v_u_3;
